#!/usr/bin/env python3
"""
CLI script for embedding chunks and building FAISS indices.

Reads chunks JSONL, embeds with specified model, and builds FAISS index with metadata.
"""

import argparse
import json
import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
from tqdm import tqdm

# Add rag module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.models import get_embedder

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_chunks(input_path: str) -> List[Dict[str, Any]]:
    """Load chunks from JSONL file."""
    chunks = []
    
    with open(input_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                chunk = json.loads(line)
                chunks.append(chunk)
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping invalid JSON on line {line_num}: {e}")
                continue
    
    logger.info(f"Loaded {len(chunks)} chunks from {input_path}")
    return chunks


def embed_chunks(chunks: List[Dict[str, Any]], model_name: str, batch_size: int = 256, device: str = "auto") -> np.ndarray:
    """
    Embed all chunks using the specified model.
    
    Args:
        chunks: List of chunk dictionaries
        model_name: Embedding model name
        batch_size: Batch size for embedding
        device: Device to use ('auto', 'cpu', 'cuda')
        
    Returns:
        Numpy array of embeddings (n_chunks, dimension)
    """
    # Get embedder
    embedder_wrapper = get_embedder(model_name)
    model = embedder_wrapper.model
    dimension = embedder_wrapper.dimension
    
    logger.info(f"Using embedder: {model_name} (dim={dimension})")
    
    # Extract texts
    texts = []
    for chunk in chunks:
        text = chunk.get("text", "")
        if not text:
            logger.warning(f"Empty text in chunk: {chunk.get('chunk_id', 'unknown')}")
            text = " "  # Use space for empty texts
        texts.append(text)
    
    # Embed in batches
    all_embeddings = []
    
    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding chunks"):
        batch_texts = texts[i:i + batch_size]
        
        try:
            batch_embeddings = model.encode(batch_texts, convert_to_numpy=True)
            all_embeddings.append(batch_embeddings)
        except Exception as e:
            logger.error(f"Error embedding batch {i//batch_size + 1}: {e}")
            # Create zero embeddings for failed batch
            zero_embeddings = np.zeros((len(batch_texts), dimension), dtype=np.float32)
            all_embeddings.append(zero_embeddings)
    
    # Concatenate all embeddings
    embeddings = np.vstack(all_embeddings)
    
    logger.info(f"Generated embeddings: {embeddings.shape}")
    return embeddings


def build_faiss_index(embeddings: np.ndarray, index_type: str = "IndexFlatIP") -> Any:
    """
    Build FAISS index from embeddings.
    
    Args:
        embeddings: Numpy array of embeddings
        index_type: Type of FAISS index to build
        
    Returns:
        FAISS index object
    """
    try:
        import faiss
    except ImportError as e:
        raise ImportError("faiss-cpu not available. Install with: pip install faiss-cpu") from e
    
    dimension = embeddings.shape[1]
    n_vectors = embeddings.shape[0]
    
    logger.info(f"Building FAISS index: {index_type}, dim={dimension}, vectors={n_vectors}")
    
    # Create index
    if index_type == "IndexFlatIP":
        index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity)
    elif index_type == "IndexFlatL2":
        index = faiss.IndexFlatL2(dimension)  # L2 distance
    else:
        raise ValueError(f"Unsupported index type: {index_type}")
    
    # Add vectors to index
    index.add(embeddings.astype(np.float32))
    
    logger.info(f"FAISS index built with {index.ntotal} vectors")
    return index


def save_faiss_index(index: Any, output_path: str):
    """Save FAISS index to file."""
    try:
        import faiss
    except ImportError:
        raise ImportError("faiss-cpu not available")
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    faiss.write_index(index, str(output_path))
    logger.info(f"Saved FAISS index to: {output_path}")


def save_metadata(chunks: List[Dict[str, Any]], embeddings: np.ndarray, model_name: str, 
                 index_path: str, stats_path: str):
    """Save metadata and statistics."""
    
    # Create stats
    stats = {
        "model_name": model_name,
        "dimension": embeddings.shape[1],
        "n_vectors": embeddings.shape[0],
        "index_path": str(index_path),
        "created_at": time.strftime('%Y-%m-%d %H:%M:%S'),
        "chunk_count": len(chunks),
        "embedding_shape": list(embeddings.shape)
    }
    
    # Save stats
    stats_path = Path(stats_path)
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)
    
    logger.info(f"Saved stats to: {stats_path}")
    
    # Save chunk metadata
    metadata_path = stats_path.with_suffix('.meta.jsonl')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    logger.info(f"Saved metadata to: {metadata_path}")


def verify_index(index_path: str, stats_path: str, expected_model: str) -> bool:
    """Verify that the built index matches expectations."""
    try:
        import faiss
        
        # Load and verify index
        index = faiss.read_index(index_path)
        
        # Load and verify stats
        with open(stats_path, 'r') as f:
            stats = json.load(f)
        
        # Check consistency
        if index.ntotal != stats["n_vectors"]:
            logger.error(f"Index vector count mismatch: index={index.ntotal}, stats={stats['n_vectors']}")
            return False
        
        if stats["model_name"] != expected_model:
            logger.error(f"Model name mismatch: stats={stats['model_name']}, expected={expected_model}")
            return False
        
        logger.info("Index verification passed")
        return True
        
    except Exception as e:
        logger.error(f"Index verification failed: {e}")
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Embed chunks and build FAISS index")
    
    parser.add_argument("--in", required=True, help="Input chunks JSONL file")
    parser.add_argument("--out", required=True, help="Output FAISS index file")
    parser.add_argument("--stats", required=True, help="Output stats JSON file")
    parser.add_argument("--model", required=True, help="Embedding model name")
    parser.add_argument("--batch-size", type=int, default=256, help="Batch size for embedding")
    parser.add_argument("--device", default="auto", help="Device to use (auto, cpu, cuda)")
    parser.add_argument("--index-type", default="IndexFlatIP", help="FAISS index type")
    parser.add_argument("--verify", action="store_true", help="Verify index after building")
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    try:
        # Load chunks
        logger.info("Loading chunks...")
        chunks = load_chunks(getattr(args, 'in'))
        
        if not chunks:
            logger.error("No chunks loaded")
            sys.exit(1)
        
        # Embed chunks
        logger.info("Embedding chunks...")
        embeddings = embed_chunks(chunks, args.model, args.batch_size, args.device)
        
        # Build FAISS index
        logger.info("Building FAISS index...")
        index = build_faiss_index(embeddings, args.index_type)
        
        # Save index
        logger.info("Saving FAISS index...")
        save_faiss_index(index, args.out)
        
        # Save metadata
        logger.info("Saving metadata...")
        save_metadata(chunks, embeddings, args.model, args.out, args.stats)
        
        # Verify if requested
        if args.verify:
            logger.info("Verifying index...")
            if not verify_index(args.out, args.stats, args.model):
                logger.error("Index verification failed")
                sys.exit(1)
        
        # Calculate timing
        total_time = time.time() - start_time
        
        # Print summary
        print(f"\n✅ Embedding and indexing complete!")
        print(f"   Chunks processed: {len(chunks)}")
        print(f"   Embedding dimension: {embeddings.shape[1]}")
        print(f"   FAISS vectors: {index.ntotal}")
        print(f"   Processing time: {total_time:.2f}s")
        print(f"   Index file: {args.out}")
        print(f"   Stats file: {args.stats}")
        
        # Save timing log
        timing_log = {
            "stage": "embed_and_index",
            "model_name": args.model,
            "chunk_count": len(chunks),
            "dimension": embeddings.shape[1],
            "total_time_seconds": total_time,
            "index_type": args.index_type,
            "batch_size": args.batch_size
        }
        
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        timing_file = logs_dir / f"embed_timing_{int(time.time())}.json"
        with open(timing_file, 'w') as f:
            json.dump(timing_log, f, indent=2)
        
        logger.info(f"Timing log saved to: {timing_file}")
        
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
