"""FAISS indexer for vector storage and retrieval."""

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np
import pandas as pd
from tqdm import tqdm

from .embeddings import EmbeddingBackend
from .io_utils import ensure_directory
from .types import Chunk, ChunkMetadata, SearchResult


class Indexer:
    """FAISS indexer for storing and retrieving chunk embeddings."""
    
    def __init__(self, index_path: Path, embedding_backend: EmbeddingBackend, eval_mode: bool = False):
        """
        Initialize indexer.
        
        Args:
            index_path: Path to store index files
            embedding_backend: Backend for generating embeddings
            eval_mode: Whether to output in evaluation system format
        """
        self.index_path = index_path
        self.embedding_backend = embedding_backend
        self.dimension = embedding_backend.dimension
        self.eval_mode = eval_mode
        
        # FAISS index
        self.index: Optional[faiss.IndexFlatIP] = None
        self.docstore: List[ChunkMetadata] = []
        self.chunks: List[Chunk] = []  # Store full chunks for eval mode
        
        # Load existing index if it exists
        self._load_index()
    
    def _load_index(self) -> None:
        """Load existing index and docstore."""
        index_file = self.index_path / "index.faiss"
        docstore_file = self.index_path / "docstore.pkl"
        
        if index_file.exists() and docstore_file.exists():
            try:
                # Load FAISS index
                self.index = faiss.read_index(str(index_file))
                
                # Load docstore
                with open(docstore_file, 'rb') as f:
                    self.docstore = pickle.load(f)
                
                print(f"Loaded existing index with {len(self.docstore)} chunks")
            except Exception as e:
                print(f"Error loading existing index: {e}. Creating new index.")
                self._create_new_index()
        else:
            self._create_new_index()
    
    def _create_new_index(self) -> None:
        """Create new FAISS index."""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.docstore = []
        print(f"Created new index with dimension {self.dimension}")
    
    def add_chunks(self, chunks: List[Chunk]) -> None:
        """
        Add chunks to the index.
        
        Args:
            chunks: List of chunks to add
        """
        if not chunks:
            return
        
        # Generate embeddings
        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_backend.embed_batch(texts)
        
        # Normalize embeddings for cosine similarity
        embeddings_array = np.array(embeddings).astype('float32')
        faiss.normalize_L2(embeddings_array)
        
        # Add to index
        self.index.add(embeddings_array)
        
        # Add to docstore and chunks
        for chunk in chunks:
            self.docstore.append(chunk.metadata)
            if self.eval_mode:
                self.chunks.append(chunk)
        
        print(f"Added {len(chunks)} chunks to index")
    
    def search(
        self, 
        query: str, 
        k: int = 5, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for similar chunks.
        
        Args:
            query: Search query
            k: Number of results to return
            filters: Optional filters to apply
            
        Returns:
            List of search results
        """
        if not self.index or len(self.docstore) == 0:
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_backend.embed_text(query)
        query_array = np.array([query_embedding]).astype('float32')
        faiss.normalize_L2(query_array)
        
        # Check dimension compatibility
        if query_array.shape[1] != self.index.d:
            raise ValueError(
                f"Query embedding dimension ({query_array.shape[1]}) doesn't match "
                f"index dimension ({self.index.d}). "
                f"The index was created with a different embedding backend. "
                f"Please use the same backend or recreate the index."
            )
        
        # Search
        scores, indices = self.index.search(query_array, min(k, len(self.docstore)))
        
        # Build results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            
            metadata = self.docstore[idx]
            
            # Apply filters if provided
            if filters and not self._matches_filters(metadata, filters):
                continue
            
            # Get text preview
            text_preview = self._get_text_preview(metadata)
            
            result = SearchResult(
                score=float(score),
                text_preview=text_preview,
                metadata=metadata
            )
            results.append(result)
        
        return results
    
    def _matches_filters(self, metadata: ChunkMetadata, filters: Dict[str, Any]) -> bool:
        """Check if metadata matches filters."""
        for key, value in filters.items():
            if key == "protocol_id" and metadata.protocol_id != value:
                return False
            elif key == "section_name" and metadata.section_name != value:
                return False
            elif key == "stones" and not any(stone in metadata.stones for stone in value):
                return False
            # Add more filter types as needed
        return True
    
    def _get_text_preview(self, metadata: ChunkMetadata) -> str:
        """Get text preview for metadata."""
        # This is a simplified version - in practice, you'd want to store
        # the actual text or load it from the chunks file
        return f"[{metadata.section_name}] {metadata.title}"
    
    def save_index(self) -> None:
        """Save index and docstore to disk."""
        ensure_directory(self.index_path)
        
        if self.eval_mode:
            # Evaluation system format
            # Save FAISS index with lane-specific name
            lane_name = self.index_path.name  # fast or accurate
            index_file = self.index_path / f"{lane_name}.index.faiss"
            faiss.write_index(self.index, str(index_file))
            
            # Save metadata as JSONL for evaluation system
            metadata_file = self.index_path / f"{lane_name}.meta.jsonl"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                for i, meta in enumerate(self.docstore):
                    # Get text from stored chunks if available
                    text = ""
                    if i < len(self.chunks):
                        text = self.chunks[i].text
                    
                    # Create evaluation system format
                    eval_meta = {
                        "text": text,
                        "metadata": {
                            "chunk_id": meta.chunk_id,
                            "protocol_id": meta.protocol_id,
                            "title": meta.title,
                            "section_name": meta.section_name,
                            "section_idx": meta.section_idx,
                            "chunk_idx": meta.chunk_idx,
                            "n_tokens": meta.n_tokens,
                            "source_path": meta.source_path,
                            "stones": meta.stones,
                            "created_at": meta.created_at,
                            "hash": meta.hash,
                            "profile": meta.profile if hasattr(meta, 'profile') else lane_name,
                            "fusion_info": meta.fusion_info if hasattr(meta, 'fusion_info') else None
                        }
                    }
                    f.write(json.dumps(eval_meta) + '\n')
            
            # Save stats file
            stats_file = self.index_path / f"{lane_name}.stats.json"
            stats = {
                "dim": self.dimension,
                "count": len(self.docstore),
                "lane": lane_name,
                "model_name": self.embedding_backend.name
            }
            with open(stats_file, 'w') as f:
                json.dump(stats, f)
            
            print(f"Saved eval format index with {len(self.docstore)} chunks to {self.index_path}")
        else:
            # Original format
            # Save FAISS index
            index_file = self.index_path / "index.faiss"
            faiss.write_index(self.index, str(index_file))
            
            # Save docstore
            docstore_file = self.index_path / "docstore.pkl"
            with open(docstore_file, 'wb') as f:
                pickle.dump(self.docstore, f)
            
            # Save metadata as parquet for easy inspection
            metadata_file = self.index_path / "metadata.parquet"
            if self.docstore:
                metadata_df = pd.DataFrame([meta.model_dump() for meta in self.docstore])
                metadata_df.to_parquet(metadata_file, index=False)
            
            print(f"Saved index with {len(self.docstore)} chunks to {self.index_path}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            "total_chunks": len(self.docstore),
            "embedding_dimension": self.dimension,
            "embedding_backend": self.embedding_backend.name,
            "index_path": str(self.index_path)
        }
    
    def clear_index(self) -> None:
        """Clear the index."""
        self._create_new_index()
        print("Cleared index")


def create_indexer(
    index_path: Path, 
    embedding_backend: EmbeddingBackend,
    eval_mode: bool = False
) -> Indexer:
    """
    Create a new indexer.
    
    Args:
        index_path: Path to store index files
        embedding_backend: Backend for generating embeddings
        eval_mode: Whether to output in evaluation system format
        
    Returns:
        Indexer instance
    """
    return Indexer(index_path, embedding_backend, eval_mode)
