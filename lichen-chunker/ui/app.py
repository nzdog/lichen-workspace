"""Streamlit UI for Lichen Protocol Chunker."""

import json
import tempfile
from pathlib import Path
from typing import List, Optional

import streamlit as st
import pandas as pd

# Add src to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from lichen_chunker.pipeline import create_pipeline, resolve_profile, hybrid_search
from lichen_chunker.types import ProcessingResult, SearchResult
from lichen_chunker.io_utils import create_canonical_filename


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Lichen Protocol Chunker",
        page_icon="🧩",
        layout="wide"
    )
    
    st.title("🧩 Lichen Protocol Chunker")
    st.markdown("Chunk and embed Lichen Protocol JSONs for RAG applications")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Retrieval dimension selection
        retrieval_mode = st.selectbox(
            "🔍 Retrieval Dimension",
            ["Speed", "Accuracy", "Hybrid"],
            index=0,
            help="Choose retrieval mode: Speed (fast/sbert), Accuracy (precise/openai), or Hybrid (query-time fusion)"
        )
        
        # Show effective settings for the selected mode
        if retrieval_mode in ["Speed", "Accuracy"]:
            profile_config = resolve_profile(retrieval_mode.lower())
            st.info(f"""
            **{retrieval_mode} Mode Settings:**
            - Backend: {profile_config['backend']}
            - Max Tokens: {profile_config['max_tokens']}
            - Overlap: {profile_config['overlap_tokens']}
            - Validation: {profile_config['validation']}
            - Save Chunks: {profile_config['save_chunks']}
            """)
        elif retrieval_mode == "Hybrid":
            st.info("""
            **Hybrid Mode:**
            - Uses both Speed and Accuracy indexes
            - Query-time fusion with RRF or weighting
            - Returns best results from both dimensions
            """)
            
            # Fusion method selection for hybrid
            fusion_method = st.selectbox(
                "Fusion Method",
                ["RRF (Reciprocal Rank Fusion)", "Weight Blend"],
                help="Method for combining results from both indexes"
            )
            
            if fusion_method == "Weight Blend":
                speed_weight = st.slider(
                    "Speed Weight",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.35,
                    step=0.05
                )
                accuracy_weight = 1.0 - speed_weight
                st.write(f"Accuracy Weight: {accuracy_weight:.2f}")
                
                # Store weights in session state
                st.session_state['fusion_weights'] = (speed_weight, accuracy_weight)
            else:
                k_rrf = st.slider(
                    "RRF Parameter (k)",
                    min_value=10,
                    max_value=100,
                    value=60,
                    help="Lower values emphasize top rankings more"
                )
                st.session_state['k_rrf'] = k_rrf
        
        # Search parameters
        st.header("Search")
        top_k = st.slider(
            "Top-K Results",
            min_value=1,
            max_value=20,
            value=5
        )
    
    # Initialize pipeline based on retrieval mode
    def get_pipeline(retrieval_mode_param):
        # Use path relative to project root (parent of ui directory)
        project_root = Path(__file__).parent.parent
        
        if retrieval_mode_param in ["Speed", "Accuracy"]:
            # Use profile-based pipeline
            return create_pipeline(
                profile=retrieval_mode_param.lower(),
                index_path=project_root / "index"
            )
        else:
            # Hybrid mode - we'll need both pipelines
            return None  # Will handle hybrid search separately
    
    # Create pipeline based on retrieval mode
    pipeline = get_pipeline(retrieval_mode)
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["📁 Upload & Process", "🔍 Search", "📊 Statistics"])
    
    with tab1:
        st.header("Upload Protocol Files")
        
        # File uploader
        uploaded_files = st.file_uploader(
            "Drop Lichen Protocol JSON files",
            accept_multiple_files=True,
            type=["json"],
            help="Upload one or more protocol JSON files to process"
        )
        
        if uploaded_files:
            # Process files button
            if st.button("🚀 Process Files", type="primary"):
                process_files(uploaded_files, retrieval_mode)
        
        # Process from folder option
        st.subheader("Or Process from Folder")
        folder_path = st.text_input(
            "Folder Path",
            value="./samples",
            help="Path to folder containing protocol JSON files"
        )
        
        if st.button("📂 Process Folder"):
            process_folder(folder_path, retrieval_mode)
    
    with tab2:
        st.header("Search Index")
        
        # Search interface
        query = st.text_input(
            "Search Query",
            placeholder="Enter your search query...",
            help="Search for similar content in the indexed protocols"
        )
        
        if query:
            try:
                # Handle different retrieval modes
                if retrieval_mode == "Hybrid":
                    # Use hybrid search with both indexes
                    project_root = Path(__file__).parent.parent
                    
                    if fusion_method == "Weight Blend":
                        search_results = hybrid_search(
                            query=query,
                            k=top_k,
                            base_index_path=project_root / "index",
                            weight_blend=st.session_state.get('fusion_weights', (0.35, 0.65))
                        )
                    else:
                        search_results = hybrid_search(
                            query=query,
                            k=top_k,
                            base_index_path=project_root / "index",
                            k_rrf=st.session_state.get('k_rrf', 60)
                        )
                    display_hybrid_search_results(search_results, fusion_method)
                else:
                    # Use single pipeline search
                    if pipeline is None:
                        st.error("Pipeline not initialized. Please check your configuration.")
                        return
                    
                    search_results = pipeline.search(query, k=top_k)
                    display_search_results(search_results)
                    
            except ValueError as e:
                if "dimension" in str(e).lower():
                    st.error(
                        "🔄 **Embedding Backend Mismatch**\n\n"
                        f"The current embedding backend doesn't match the index. "
                        f"The index was created with **OpenAI** embeddings (3072D), "
                        f"but you're trying to search with a different backend.\n\n"
                        f"**Solution**: Change the Retrieval Dimension in the sidebar "
                        f"and refresh the page, or recreate the index with the current backend."
                    )
                else:
                    st.error(f"Search error: {e}")
            except Exception as e:
                st.error(f"Unexpected search error: {e}")
    
    with tab3:
        st.header("Index Statistics")
        display_statistics(retrieval_mode)


def process_files(uploaded_files: List, retrieval_mode: str) -> None:
    """Process uploaded files."""
    with st.spinner("Processing files..."):
        # Use path relative to project root (parent of ui directory)
        project_root = Path(__file__).parent.parent
        uploads_dir = project_root / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        
        # Save uploaded files first
        file_paths = []
        for uploaded_file in uploaded_files:
            # Create canonical filename from original name
            canonical_filename = create_canonical_filename(uploaded_file.name)
            canonical_path = uploads_dir / canonical_filename
            
            # Save uploaded file to uploads directory with canonical name
            with open(canonical_path, 'w', encoding='utf-8') as f:
                f.write(uploaded_file.getvalue().decode('utf-8'))
            file_paths.append(canonical_path)
        
        # Process based on retrieval mode
        if retrieval_mode == "Hybrid":
            # Process with both profiles
            st.info("Processing with both Speed and Accuracy profiles for hybrid retrieval...")
            
            # Process Speed profile with progress bar
            st.write("📈 Processing Speed profile...")
            speed_pipeline = create_pipeline(
                profile="speed",
                index_path=project_root / "index"
            )
            
            # Create progress bar for Speed profile
            speed_progress_bar = st.progress(0)
            speed_status_text = st.empty()
            
            speed_results = []
            for i, file_path in enumerate(file_paths):
                speed_status_text.text(f"Processing {file_path.name} ({i+1}/{len(file_paths)})")
                result = speed_pipeline.process_file(
                    file_path,
                    output_dir=project_root / "data",
                    schema_path=project_root / "libs" / "protocol_template_schema_v1.json"
                )
                speed_results.append(result)
                speed_progress_bar.progress((i + 1) / len(file_paths))
            
            speed_pipeline.save_index()
            
            # Process Accuracy profile with progress bar
            st.write("🎯 Processing Accuracy profile...")
            accuracy_pipeline = create_pipeline(
                profile="accuracy",
                index_path=project_root / "index"
            )
            
            # Create progress bar for Accuracy profile
            accuracy_progress_bar = st.progress(0)
            accuracy_status_text = st.empty()
            
            accuracy_results = []
            for i, file_path in enumerate(file_paths):
                accuracy_status_text.text(f"Processing {file_path.name} ({i+1}/{len(file_paths)})")
                result = accuracy_pipeline.process_file(
                    file_path,
                    output_dir=project_root / "data",
                    schema_path=project_root / "libs" / "protocol_template_schema_v1.json"
                )
                accuracy_results.append(result)
                accuracy_progress_bar.progress((i + 1) / len(file_paths))
            
            accuracy_pipeline.save_index()
            
            # Clear progress indicators
            speed_progress_bar.empty()
            accuracy_progress_bar.empty()
            speed_status_text.empty()
            accuracy_status_text.empty()
            
            # Display dual results
            display_dual_processing_results(speed_results, accuracy_results)
            
        else:
            # Single profile processing with progress bar
            pipeline = create_pipeline(
                profile=retrieval_mode.lower(),
                index_path=project_root / "index"
            )
            
            # Create progress bar for single profile
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = []
            for i, file_path in enumerate(file_paths):
                status_text.text(f"Processing {file_path.name} ({i+1}/{len(file_paths)})")
                result = pipeline.process_file(
                    file_path,
                    output_dir=project_root / "data",
                    schema_path=project_root / "libs" / "protocol_template_schema_v1.json"
                )
                results.append(result)
                progress_bar.progress((i + 1) / len(file_paths))
            
            # Save index
            pipeline.save_index()
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            # Display results
            display_processing_results(results, retrieval_mode, pipeline)


def process_folder(folder_path: str, retrieval_mode: str) -> None:
    """Process files from folder."""
    folder = Path(folder_path)
    
    if not folder.exists():
        st.error(f"Folder not found: {folder_path}")
        return
    
    with st.spinner("Processing folder..."):
        # Use paths relative to project root (parent of ui directory)
        project_root = Path(__file__).parent.parent
        
        # Process based on retrieval mode
        if retrieval_mode == "Hybrid":
            # Process with both profiles
            st.info("Processing folder with both Speed and Accuracy profiles for hybrid retrieval...")
            
            # Process Speed profile with progress indicator
            st.write("📈 Processing Speed profile...")
            with st.spinner("Processing files with Speed profile..."):
                speed_pipeline = create_pipeline(
                    profile="speed",
                    index_path=project_root / "index"
                )
                speed_results = speed_pipeline.process_directory(
                    folder,
                    patterns=["*.json"],
                    output_dir=project_root / "data",
                    schema_path=project_root / "libs" / "protocol_template_schema_v1.json"
                )
                speed_pipeline.save_index()
            
            # Process Accuracy profile with progress indicator
            st.write("🎯 Processing Accuracy profile...")
            with st.spinner("Processing files with Accuracy profile..."):
                accuracy_pipeline = create_pipeline(
                    profile="accuracy",
                    index_path=project_root / "index"
                )
                accuracy_results = accuracy_pipeline.process_directory(
                    folder,
                    patterns=["*.json"],
                    output_dir=project_root / "data",
                    schema_path=project_root / "libs" / "protocol_template_schema_v1.json"
                )
                accuracy_pipeline.save_index()
            
            # Display dual results
            display_dual_processing_results(speed_results, accuracy_results)
            
        else:
            # Single profile processing with progress indicator
            with st.spinner(f"Processing files with {retrieval_mode} profile..."):
                pipeline = create_pipeline(
                    profile=retrieval_mode.lower(),
                    index_path=project_root / "index"
                )
                
                results = pipeline.process_directory(
                    folder,
                    patterns=["*.json"],
                    output_dir=project_root / "data",
                    schema_path=project_root / "libs" / "protocol_template_schema_v1.json"
                )
                
                # Save index
                pipeline.save_index()
            
            # Display results
            display_processing_results(results, retrieval_mode, pipeline)


def display_processing_results(results: List[ProcessingResult], profile: str = "Custom", pipeline=None) -> None:
    """Display processing results."""
    st.subheader("Processing Results")
    
    # Summary
    total_files = len(results)
    valid_files = sum(1 for r in results if r.valid)
    total_chunks = sum(r.chunks_created for r in results if r.valid)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Files", total_files)
    with col2:
        st.metric("Valid Files", valid_files)
    with col3:
        st.metric("Total Chunks", total_chunks)
    with col4:
        st.metric("Profile", profile)
    
    # Profile-specific info
    if profile in ["Speed", "Accuracy"] and pipeline:
        config = resolve_profile(profile.lower())
        stats = pipeline.get_stats()
        
        st.info(f"""
        **{profile} Profile Summary:**
        - Backend: {stats.get('embedding_backend', 'Unknown')}
        - Validation: {'✅' if config.get('validation', True) else '❌ Skipped'}
        - Chunk Files: {'✅ Saved' if config.get('save_chunks', True) else '❌ Not saved'}
        - Duplicate Check: {'✅' if config.get('duplicate_check', True) else '❌ Skipped'}
        """)
        
        if not config.get('save_chunks', True):
            st.warning("⚡ Speed mode: Chunk files not saved to disk")
        if not config.get('validation', True):
            st.warning("⚡ Speed mode: Schema validation skipped")
    
    # Results table
    if results:
        df = pd.DataFrame([
            {
                "File": Path(r.file_path).name,
                "Valid": "✅" if r.valid else "❌",
                "Chunks": r.chunks_created,
                "Output": Path(r.chunks_file).name if r.chunks_file else "",
                "Error": r.error_message or ""
            }
            for r in results
        ])
        
        st.dataframe(df, width='stretch')
        
        # Download links for chunk files
        if valid_files > 0:
            st.subheader("Download Chunk Files")
            for result in results:
                if result.valid and result.chunks_file:
                    chunk_file = Path(result.chunks_file)
                    if chunk_file.exists():
                        with open(chunk_file, 'r') as f:
                            chunk_data = f.read()
                        
                        st.download_button(
                            label=f"Download {chunk_file.name}",
                            data=chunk_data,
                            file_name=chunk_file.name,
                            mime="application/json"
                        )


def display_search_results(results: List[SearchResult]) -> None:
    """Display search results."""
    if not results:
        st.warning("No results found")
        return
    
    st.subheader(f"Search Results ({len(results)} found)")
    
    for i, result in enumerate(results, 1):
        with st.expander(f"Result {i} - Score: {result.score:.3f}"):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.write("**Protocol:**", result.metadata.title)
                st.write("**Section:**", result.metadata.section_name)
                st.write("**Chunk ID:**", result.metadata.chunk_id)
                st.write("**Tokens:**", result.metadata.n_tokens)
                if hasattr(result.metadata, 'profile') and result.metadata.profile:
                    st.write("**Profile:**", result.metadata.profile)
                
                if result.metadata.stones:
                    st.write("**Stones:**", ", ".join(result.metadata.stones))
            
            with col2:
                st.write("**Preview:**")
                st.text(result.text_preview)


def display_hybrid_search_results(results: List[SearchResult], fusion_method: str) -> None:
    """Display hybrid search results with fusion information."""
    if not results:
        st.warning("No results found")
        return
    
    st.subheader(f"Hybrid Search Results ({len(results)} found)")
    st.info(f"Using {fusion_method} for query-time fusion")
    
    # Summary table showing fusion details
    with st.expander("🔍 Fusion Details", expanded=True):
        fusion_df = pd.DataFrame([
            {
                "Rank": i + 1,
                "Profile": getattr(result.metadata, 'profile', 'unknown'),
                "Fused Score": f"{result.score:.4f}",
                "Protocol": result.metadata.title,
                "Section": result.metadata.section_name
            }
            for i, result in enumerate(results)
        ])
        st.dataframe(fusion_df, use_container_width=True)
    
    # Detailed results
    for i, result in enumerate(results, 1):
        with st.expander(f"Result {i} - Fused Score: {result.score:.4f}"):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.write("**Protocol:**", result.metadata.title)
                st.write("**Section:**", result.metadata.section_name)
                st.write("**Profile:**", getattr(result.metadata, 'profile', 'unknown'))
                st.write("**Chunk ID:**", result.metadata.chunk_id)
                st.write("**Tokens:**", result.metadata.n_tokens)
                
                if result.metadata.stones:
                    st.write("**Stones:**", ", ".join(result.metadata.stones))
            
            with col2:
                st.write("**Preview:**")
                st.text(result.text_preview)


def display_dual_processing_results(speed_results: List[ProcessingResult], accuracy_results: List[ProcessingResult]) -> None:
    """Display dual processing results for hybrid mode."""
    st.subheader("Dual Processing Results")
    
    # Summary metrics
    speed_valid = sum(1 for r in speed_results if r.valid)
    speed_chunks = sum(r.chunks_created for r in speed_results if r.valid)
    accuracy_valid = sum(1 for r in accuracy_results if r.valid)
    accuracy_chunks = sum(r.chunks_created for r in accuracy_results if r.valid)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Speed Valid", speed_valid)
    with col2:
        st.metric("Speed Chunks", speed_chunks)
    with col3:
        st.metric("Accuracy Valid", accuracy_valid)
    with col4:
        st.metric("Accuracy Chunks", accuracy_chunks)
    
    # Profile comparison
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Speed Profile Results")
        speed_df = pd.DataFrame([
            {
                "File": Path(r.file_path).name,
                "Valid": "✅" if r.valid else "❌",
                "Chunks": r.chunks_created,
                "Output": Path(r.chunks_file).name if r.chunks_file else "",
                "Error": r.error_message or ""
            }
            for r in speed_results
        ])
        st.dataframe(speed_df, use_container_width=True)
    
    with col2:
        st.subheader("🎯 Accuracy Profile Results")
        accuracy_df = pd.DataFrame([
            {
                "File": Path(r.file_path).name,
                "Valid": "✅" if r.valid else "❌",
                "Chunks": r.chunks_created,
                "Output": Path(r.chunks_file).name if r.chunks_file else "",
                "Error": r.error_message or ""
            }
            for r in accuracy_results
        ])
        st.dataframe(accuracy_df, use_container_width=True)
    
    # Download links
    st.subheader("Download Chunk Files")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Speed Profile Chunks:**")
        for result in speed_results:
            if result.valid and result.chunks_file:
                chunk_file = Path(result.chunks_file)
                if chunk_file.exists():
                    with open(chunk_file, 'r') as f:
                        chunk_data = f.read()
                    st.download_button(
                        label=f"📈 {chunk_file.name}",
                        data=chunk_data,
                        file_name=chunk_file.name,
                        mime="application/json"
                    )
    
    with col2:
        st.write("**Accuracy Profile Chunks:**")
        for result in accuracy_results:
            if result.valid and result.chunks_file:
                chunk_file = Path(result.chunks_file)
                if chunk_file.exists():
                    with open(chunk_file, 'r') as f:
                        chunk_data = f.read()
                    st.download_button(
                        label=f"🎯 {chunk_file.name}",
                        data=chunk_data,
                        file_name=chunk_file.name,
                        mime="application/json"
                    )


def display_statistics(retrieval_mode: str) -> None:
    """Display index statistics."""
    project_root = Path(__file__).parent.parent
    
    if retrieval_mode == "Hybrid":
        # Display statistics for both indexes
        st.subheader("Hybrid Index Statistics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("### 📈 Speed Index")
            try:
                speed_pipeline = create_pipeline(profile="speed", index_path=project_root / "index")
                speed_stats = speed_pipeline.get_stats()
                
                if speed_stats["total_chunks"] == 0:
                    st.info("No chunks in speed index.")
                else:
                    st.metric("Speed Chunks", speed_stats["total_chunks"])
                    st.metric("Speed Backend", speed_stats["embedding_backend"])
                    st.metric("Speed Dimension", speed_stats["embedding_dimension"])
                    
                    with st.expander("Speed Index Details"):
                        st.json(speed_stats)
            except Exception as e:
                st.error(f"Error loading speed index: {e}")
        
        with col2:
            st.write("### 🎯 Accuracy Index")
            try:
                accuracy_pipeline = create_pipeline(profile="accuracy", index_path=project_root / "index")
                accuracy_stats = accuracy_pipeline.get_stats()
                
                if accuracy_stats["total_chunks"] == 0:
                    st.info("No chunks in accuracy index.")
                else:
                    st.metric("Accuracy Chunks", accuracy_stats["total_chunks"])
                    st.metric("Accuracy Backend", accuracy_stats["embedding_backend"])
                    st.metric("Accuracy Dimension", accuracy_stats["embedding_dimension"])
                    
                    with st.expander("Accuracy Index Details"):
                        st.json(accuracy_stats)
            except Exception as e:
                st.error(f"Error loading accuracy index: {e}")
                
    else:
        # Single profile statistics
        try:
            pipeline = create_pipeline(profile=retrieval_mode.lower(), index_path=project_root / "index")
            stats = pipeline.get_stats()
            
            if stats["total_chunks"] == 0:
                st.info("No chunks in index. Process some files first.")
                return
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Chunks", stats["total_chunks"])
            
            with col2:
                st.metric("Embedding Dimension", stats["embedding_dimension"])
            
            with col3:
                st.metric("Backend", stats["embedding_backend"])
            
            with col4:
                st.metric("Profile", retrieval_mode)
            
            # Additional info
            st.subheader("Index Information")
            st.json(stats)
            
        except Exception as e:
            st.error(f"Error loading {retrieval_mode.lower()} index: {e}")


if __name__ == "__main__":
    main()

