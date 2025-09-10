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

from lichen_chunker.pipeline import create_pipeline
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
        
        # Embedding backend
        backend = st.selectbox(
            "Embedding Backend",
            ["auto", "openai", "sbert"],
            help="Auto will use OpenAI if API key is available, otherwise SBERT"
        )
        
        # Chunking parameters
        max_tokens = st.slider(
            "Max Tokens per Chunk",
            min_value=200,
            max_value=1000,
            value=600,
            step=50
        )
        
        overlap_tokens = st.slider(
            "Overlap Tokens",
            min_value=0,
            max_value=200,
            value=60,
            step=10
        )
        
        # Search parameters
        st.header("Search")
        top_k = st.slider(
            "Top-K Results",
            min_value=1,
            max_value=20,
            value=5
        )
    
    # Initialize pipeline - temporarily disable caching to fix backend mismatch
    def get_pipeline(backend_param, max_tokens_param, overlap_tokens_param):
        # Use path relative to project root (parent of ui directory)
        project_root = Path(__file__).parent.parent
        return create_pipeline(
            backend=backend_param,
            max_tokens=max_tokens_param,
            overlap_tokens=overlap_tokens_param,
            index_path=project_root / "index"
        )
    
    # Create fresh pipeline each time until caching issues are resolved
    pipeline = get_pipeline(backend, max_tokens, overlap_tokens)
    
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
                process_files(uploaded_files, pipeline)
        
        # Process from folder option
        st.subheader("Or Process from Folder")
        folder_path = st.text_input(
            "Folder Path",
            value="./samples",
            help="Path to folder containing protocol JSON files"
        )
        
        if st.button("📂 Process Folder"):
            process_folder(folder_path, pipeline)
    
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
                search_results = pipeline.search(query, k=top_k)
                display_search_results(search_results)
            except ValueError as e:
                if "dimension" in str(e).lower():
                    st.error(
                        "🔄 **Embedding Backend Mismatch**\n\n"
                        f"The current embedding backend doesn't match the index. "
                        f"The index was created with **OpenAI** embeddings (3072D), "
                        f"but you're trying to search with a different backend.\n\n"
                        f"**Solution**: Set the Embedding Backend to **'openai'** in the sidebar "
                        f"and refresh the page, or recreate the index with the current backend."
                    )
                else:
                    st.error(f"Search error: {e}")
            except Exception as e:
                st.error(f"Unexpected search error: {e}")
    
    with tab3:
        st.header("Index Statistics")
        display_statistics(pipeline)


def process_files(uploaded_files: List, pipeline) -> None:
    """Process uploaded files."""
    with st.spinner("Processing files..."):
        results = []
        # Use path relative to project root (parent of ui directory)
        project_root = Path(__file__).parent.parent
        uploads_dir = project_root / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        
        for uploaded_file in uploaded_files:
            # Create canonical filename from original name
            canonical_filename = create_canonical_filename(uploaded_file.name)
            canonical_path = uploads_dir / canonical_filename
            
            # Save uploaded file to uploads directory with canonical name
            with open(canonical_path, 'w', encoding='utf-8') as f:
                f.write(uploaded_file.getvalue().decode('utf-8'))
            
            # Process file using the canonical path
            # Use paths relative to project root (parent of ui directory)
            project_root = Path(__file__).parent.parent
            result = pipeline.process_file(
                canonical_path,
                output_dir=project_root / "data",
                schema_path=project_root / "libs" / "protocol_template_schema_v1.json"
            )
            results.append(result)
        
        # Save index
        pipeline.save_index()
        
        # Display results
        display_processing_results(results)


def process_folder(folder_path: str, pipeline) -> None:
    """Process files from folder."""
    folder = Path(folder_path)
    
    if not folder.exists():
        st.error(f"Folder not found: {folder_path}")
        return
    
    with st.spinner("Processing folder..."):
        # Use paths relative to project root (parent of ui directory)
        project_root = Path(__file__).parent.parent
        results = pipeline.process_directory(
            folder,
            patterns=["*.json"],
            output_dir=project_root / "data",
            schema_path=project_root / "libs" / "protocol_template_schema_v1.json"
        )
        
        # Save index
        pipeline.save_index()
        
        # Display results
        display_processing_results(results)


def display_processing_results(results: List[ProcessingResult]) -> None:
    """Display processing results."""
    st.subheader("Processing Results")
    
    # Summary
    total_files = len(results)
    valid_files = sum(1 for r in results if r.valid)
    total_chunks = sum(r.chunks_created for r in results if r.valid)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Files", total_files)
    with col2:
        st.metric("Valid Files", valid_files)
    with col3:
        st.metric("Total Chunks", total_chunks)
    
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
                
                if result.metadata.stones:
                    st.write("**Stones:**", ", ".join(result.metadata.stones))
            
            with col2:
                st.write("**Preview:**")
                st.text(result.text_preview)


def display_statistics(pipeline) -> None:
    """Display index statistics."""
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
        st.metric("Index Path", stats["index_path"])
    
    # Additional info
    st.subheader("Index Information")
    st.json(stats)


if __name__ == "__main__":
    main()

