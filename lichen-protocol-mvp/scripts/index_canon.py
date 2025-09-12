#!/usr/bin/env python3
"""
Index protocol canon JSONs to vector store for RAG retrieval.

This script walks the protocol canon JSONs, chunks them deterministically,
embeds the chunks, and upserts them to the configured vector store.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml


def load_config(config_path: str) -> Dict[str, Any]:
    """Load RAG configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_protocol_schema() -> Dict[str, Any]:
    """Load the protocol schema to understand the structure."""
    schema_path = Path("../../lichen-chunker/libs/protocol_template_schema_v1.json")
    if not schema_path.exists():
        # Fallback to a basic schema structure
        return {
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "stones": {"type": "array", "items": {"type": "string"}}
            }
        }
    
    with open(schema_path, 'r') as f:
        return json.load(f)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Chunk text deterministically.
    
    Args:
        text: Text to chunk
        chunk_size: Maximum size of each chunk
        overlap: Overlap between chunks
        
    Returns:
        List of chunks with metadata
    """
    if not text:
        return []
    
    chunks = []
    words = text.split()
    
    start = 0
    chunk_id = 1
    
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)
        
        chunks.append({
            "chunk_id": chunk_id,
            "text": chunk_text,
            "start_word": start,
            "end_word": end,
            "word_count": len(chunk_words)
        })
        
        chunk_id += 1
        start = end - overlap if end < len(words) else end
    
    return chunks


def extract_protocol_content(protocol_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract and chunk content from a protocol JSON.
    
    Args:
        protocol_data: Protocol JSON data
        
    Returns:
        List of chunks with metadata
    """
    chunks = []
    
    # Extract title (try both "title" and "Title")
    title = protocol_data.get("title", protocol_data.get("Title", ""))
    if title:
        chunks.append({
            "chunk_id": 0,
            "text": f"Title: {title}",
            "type": "title",
            "start_word": 0,
            "end_word": len(title.split()),
            "word_count": len(title.split())
        })
    
    # Extract main content (try both "content" and "Content")
    content = protocol_data.get("content", protocol_data.get("Content", ""))
    if content:
        content_chunks = chunk_text(content)
        for chunk in content_chunks:
            chunk["type"] = "content"
            chunks.append(chunk)
    
    # Extract stones/principles
    stones = protocol_data.get("stones", [])
    if stones:
        stones_text = "Principles: " + "; ".join(stones)
        chunks.append({
            "chunk_id": len(chunks),
            "text": stones_text,
            "type": "stones",
            "start_word": 0,
            "end_word": len(stones_text.split()),
            "word_count": len(stones_text.split())
        })
    
    # Extract other relevant fields
    for field in ["description", "purpose", "context", "Overall Purpose", "Why This Matters", "When To Use This Protocol"]:
        if field in protocol_data and protocol_data[field]:
            field_text = str(protocol_data[field])
            field_chunks = chunk_text(field_text)
            for chunk in field_chunks:
                chunk["type"] = field.lower().replace(" ", "_")
                chunks.append(chunk)
    
    # Extract themes if present
    themes = protocol_data.get("Themes", [])
    for theme in themes:
        if isinstance(theme, dict):
            theme_name = theme.get("Name", "")
            theme_purpose = theme.get("Purpose of This Theme", "")
            theme_why = theme.get("Why This Matters", "")
            
            if theme_name:
                theme_text = f"Theme: {theme_name}"
                if theme_purpose:
                    theme_text += f" - {theme_purpose}"
                if theme_why:
                    theme_text += f" - {theme_why}"
                
                theme_chunks = chunk_text(theme_text)
                for chunk in theme_chunks:
                    chunk["type"] = "theme"
                    chunks.append(chunk)
    
    return chunks


def embed_chunks(chunks: List[Dict[str, Any]], embed_model: str, lane: str = "fast") -> List[Dict[str, Any]]:
    """
    Embed chunks using the specified model.
    
    Args:
        chunks: List of text chunks
        embed_model: Embedding model name
        lane: Lane name for logging
        
    Returns:
        List of chunks with embeddings
    """
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        # Load embedding model
        print(f"Loading {lane} lane embedding model: {embed_model}")
        model = SentenceTransformer(embed_model)
        
        # Extract texts for embedding
        texts = [chunk["text"] for chunk in chunks]
        
        # Generate embeddings
        print(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = model.encode(texts, show_progress_bar=True)
        
        # Add embeddings to chunks
        for i, chunk in enumerate(chunks):
            # Normalize embedding to unit length for cosine similarity
            embedding = embeddings[i]
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            chunk["embedding"] = embedding.tolist()
        
        print(f"Generated {len(embeddings)} embeddings with dimension {embeddings.shape[1]}")
        return chunks
        
    except ImportError:
        print("Warning: sentence-transformers not available, using dummy embeddings")
        for chunk in chunks:
            chunk["embedding"] = [0.0] * 384  # Dummy embedding vector
        return chunks
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        for chunk in chunks:
            chunk["embedding"] = [0.0] * 384  # Dummy embedding vector
        return chunks


def upsert_to_vector_store(chunks: List[Dict[str, Any]], config: Dict[str, Any], lane: str = "fast") -> None:
    """
    Upsert chunks to the configured vector store.
    
    Args:
        chunks: List of chunks with embeddings
        config: Vector store configuration
        lane: Lane name for per-lane paths
    """
    try:
        import faiss
        import numpy as np
        
        # Get per-lane paths or fall back to legacy
        vector_store_config = config.get("vector_store", {})
        lane_config = vector_store_config.get(lane, {})
        
        if lane_config:
            # Use per-lane paths
            output_path = Path(lane_config.get("path", f".vector/{lane}.index.faiss"))
            meta_path = Path(lane_config.get("meta", f".vector/{lane}.meta.jsonl"))
            stats_path = Path(lane_config.get("stats", f".vector/{lane}.stats.json"))
        else:
            # Fall back to legacy single-index paths
            output_path = Path(vector_store_config.get("path_or_index", ".vector/index.faiss"))
            meta_path = output_path.parent / "meta.jsonl"
            stats_path = output_path.parent / "stats.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not chunks:
            print("No chunks to index")
            return
        
        # Extract embeddings and metadata
        embeddings = []
        metadata = []
        
        for i, chunk in enumerate(chunks):
            embedding = chunk.get("embedding", [0.0] * 384)
            embeddings.append(embedding)
            
            # Create metadata entry
            meta = {
                "vector_id": i,
                "doc": chunk.get("doc_id", ""),
                "chunk": chunk.get("chunk_id", 0),
                "text": chunk.get("text", ""),
                "stones": chunk.get("stones", [])
            }
            metadata.append(meta)
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings, dtype=np.float32)
        dim = embeddings_array.shape[1]
        
        # Create FAISS index (IndexFlatIP for inner product = cosine similarity with normalized vectors)
        index = faiss.IndexFlatIP(dim)
        
        # Add vectors to index
        print(f"Building FAISS index with {len(embeddings)} vectors of dimension {dim}")
        index.add(embeddings_array)
        
        # Save FAISS index
        faiss.write_index(index, str(output_path))
        print(f"Saved FAISS index to {output_path}")
        
        # Save metadata as JSONL
        with open(meta_path, 'w') as f:
            for meta in metadata:
                f.write(json.dumps(meta) + '\n')
        print(f"Saved metadata to {meta_path}")
        
        # Save stats
        lane_config_embed = config.get(lane, {})
        stats = {
            "lane": lane,
            "model_name": lane_config_embed.get("embed_model", "sentence-transformers/all-MiniLM-L6-v2"),
            "dim": dim,
            "count": len(chunks),
            "build_time": time.time(),
            "index_type": "IndexFlatIP"
        }
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"Saved stats to {stats_path}")
        
    except ImportError:
        print("Warning: faiss not available, saving to JSON file")
        output_path = Path(config.get("path_or_index", ".vector/index.faiss"))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save chunks metadata
        metadata_path = output_path.parent / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(chunks, f, indent=2)
        
        print(f"Saved {len(chunks)} chunks to {metadata_path}")
    except Exception as e:
        print(f"Error building vector store: {e}")
        # Fallback to JSON
        output_path = Path(config.get("path_or_index", ".vector/index.faiss"))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        metadata_path = output_path.parent / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(chunks, f, indent=2)
        
        print(f"Fallback: saved {len(chunks)} chunks to {metadata_path}")


def process_manifest_file(file_path: Path, config: Dict[str, Any], lane: str = "fast") -> List[Dict[str, Any]]:
    """
    Process a manifest file containing protocol references.
    
    Args:
        file_path: Path to manifest YAML file
        config: RAG configuration
        
    Returns:
        List of processed chunks from all protocols in manifest
    """
    try:
        with open(file_path, 'r') as f:
            manifest_data = yaml.safe_load(f)
        
        all_chunks = []
        items = manifest_data.get("items", [])
        
        for item in items:
            protocol_path = item.get("path")
            if not protocol_path:
                continue
            
            # Convert absolute path to relative if needed
            if protocol_path.startswith("/"):
                # Extract just the filename and look in test-protocols
                protocol_name = Path(protocol_path).name
                protocol_path = f"../test-protocols/{protocol_name}"
            
            protocol_file = Path(protocol_path)
            if protocol_file.exists():
                print(f"  Processing protocol: {protocol_file}")
                chunks = process_protocol_file(protocol_file, config, item, lane)
                all_chunks.extend(chunks)
            else:
                print(f"  Protocol file not found: {protocol_file}")
        
        return all_chunks
        
    except Exception as e:
        print(f"Error processing manifest {file_path}: {e}")
        return []


def process_protocol_file(file_path: Path, config: Dict[str, Any], manifest_item: Dict[str, Any] = None, lane: str = "fast") -> List[Dict[str, Any]]:
    """
    Process a single protocol file.
    
    Args:
        file_path: Path to protocol JSON file
        config: RAG configuration
        manifest_item: Optional manifest item with metadata
        
    Returns:
        List of processed chunks
    """
    try:
        with open(file_path, 'r') as f:
            protocol_data = json.load(f)
        
        # Extract and chunk content
        chunks = extract_protocol_content(protocol_data)
        
        # Add document metadata
        doc_id = file_path.stem
        stones = protocol_data.get("stones", [])
        
        # Use manifest metadata if available
        if manifest_item:
            doc_id = manifest_item.get("protocol_id", doc_id)
            stones = manifest_item.get("stones", stones)
        
        for chunk in chunks:
            chunk["doc_id"] = doc_id
            chunk["source_file"] = str(file_path)
            chunk["stones"] = stones
        
        # Embed chunks using lane-specific model
        embed_model = config.get(lane, {}).get("embed_model", "sentence-transformers/all-MiniLM-L6-v2")
        chunks = embed_chunks(chunks, embed_model, lane)
        
        return chunks
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Index protocol canon to vector store")
    parser.add_argument("--config", default="config/rag.yaml", help="RAG configuration file")
    parser.add_argument("--source-glob", default="../../test-protocols/*.json", help="Source files glob pattern")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the entire index")
    parser.add_argument("--output-dir", default=".vector", help="Output directory for vector store")
    parser.add_argument("--lane", choices=["fast", "accurate"], default="fast", help="Lane to build index for")
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)
    
    # Update vector store path if specified
    if args.output_dir:
        config["vector_store"]["path_or_index"] = os.path.join(args.output_dir, "index.faiss")
    
    # Get lane from args
    lane = args.lane
    
    # Find source files
    source_pattern = Path(args.source_glob)
    if source_pattern.is_file():
        source_files = [source_pattern]
    else:
        # Handle glob pattern
        import glob
        source_files = [Path(f) for f in glob.glob(str(source_pattern))]
    
    if not source_files:
        print(f"No files found matching pattern: {args.source_glob}")
        sys.exit(1)
    
    print(f"Found {len(source_files)} files to process")
    
    # Process files
    all_chunks = []
    for file_path in source_files:
        print(f"Processing {file_path}")
        
        # Check if it's a manifest file (YAML) or protocol file (JSON)
        if file_path.suffix.lower() in ['.yaml', '.yml']:
            chunks = process_manifest_file(file_path, config, lane)
        else:
            chunks = process_protocol_file(file_path, config, None, lane)
        
        all_chunks.extend(chunks)
        print(f"  Extracted {len(chunks)} chunks")
    
    if not all_chunks:
        print("No chunks extracted from any files")
        sys.exit(1)
    
    print(f"Total chunks: {len(all_chunks)}")
    
    # Upsert to vector store
    print(f"Upserting to {lane} lane vector store...")
    upsert_to_vector_store(all_chunks, config, lane)
    
    print("Indexing complete!")


if __name__ == "__main__":
    main()
