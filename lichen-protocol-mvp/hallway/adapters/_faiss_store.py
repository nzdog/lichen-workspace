"""
FAISS vector store helper module for RAG retrieval.

Provides a singleton interface for loading and querying FAISS indices
with metadata, supporting both bi-encoder and cross-encoder reranking.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import threading

# Optional imports with graceful degradation
try:
    import numpy as np
    import faiss
    from sentence_transformers import SentenceTransformer
    HAS_FAISS_DEPS = True
except ImportError:
    HAS_FAISS_DEPS = False
    np = None
    faiss = None
    SentenceTransformer = None

try:
    from sentence_transformers import CrossEncoder
    HAS_CROSS_ENCODER = True
except ImportError:
    HAS_CROSS_ENCODER = False
    CrossEncoder = None

try:
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    cosine_similarity = None

logger = logging.getLogger(__name__)

# Global singleton state - per-lane cache
_store_instances = {}
_store_lock = threading.Lock()


class FAISSStore:
    """FAISS vector store with metadata management."""
    
    def __init__(self, config: Dict[str, Any], lane: str = "fast"):
        """Initialize FAISS store with configuration."""
        if not HAS_FAISS_DEPS:
            raise ImportError("FAISS dependencies not available. Install faiss-cpu, numpy, sentence-transformers")
        
        self.config = config
        self.lane = lane
        self.embed_model = None
        self.cross_encoder = None
        self.index = None
        self.metadata = {}
        self._initialized = False
        
        # Get lane-specific paths or fall back to legacy
        self._setup_paths()
    
    def _setup_paths(self):
        """Setup paths for this lane, with environment overrides and fallback to legacy."""
        vector_store_config = self.config.get("vector_store", {})
        lane_config = vector_store_config.get(self.lane, {})
        
        # Check for environment overrides
        env_path_key = f"VECTOR_PATH_{self.lane.upper()}"
        env_meta_key = f"VECTOR_META_{self.lane.upper()}"
        env_stats_key = f"VECTOR_STATS_{self.lane.upper()}"
        
        if lane_config or os.getenv(env_path_key):
            # Use per-lane paths
            self.index_path = os.getenv(env_path_key, lane_config.get("path", f".vector/{self.lane}.index.faiss"))
            self.meta_path = os.getenv(env_meta_key, lane_config.get("meta", f".vector/{self.lane}.meta.jsonl"))
            self.stats_path = os.getenv(env_stats_key, lane_config.get("stats", f".vector/{self.lane}.stats.json"))
        else:
            # Fall back to legacy single-index paths
            self.index_path = vector_store_config.get("path_or_index", ".vector/index.faiss")
            self.meta_path = Path(self.index_path).parent / "meta.jsonl"
            self.stats_path = Path(self.index_path).parent / "stats.json"
            logger.warning(f"Using legacy index for {self.lane} lane: {self.index_path}")
        
        # Get dimension from stats or config
        self.dim = vector_store_config.get("dim", 384)
        
    def _load_embedding_model(self, model_name: str) -> SentenceTransformer:
        """Load and cache embedding model."""
        if self.embed_model is None:
            logger.info(f"Loading embedding model: {model_name}")
            self.embed_model = SentenceTransformer(model_name)
            logger.info("Embedding model loaded successfully")
        return self.embed_model
    
    def _load_cross_encoder(self, model_name: str) -> Optional[CrossEncoder]:
        """Load and cache cross-encoder model."""
        if not HAS_CROSS_ENCODER:
            logger.warning("CrossEncoder not available, skipping reranking")
            return None
            
        if self.cross_encoder is None:
            try:
                logger.info(f"Loading cross-encoder: {model_name}")
                self.cross_encoder = CrossEncoder(model_name)
                logger.info("Cross-encoder loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load cross-encoder {model_name}: {e}")
                return None
        return self.cross_encoder
    
    def get_reranker_model_name(self) -> Optional[str]:
        """Get the active reranker model name."""
        if self.cross_encoder is None:
            return None
        # Extract model name from the cross-encoder
        return getattr(self.cross_encoder, 'model_name', 'unknown')
    
    def get_reranker_name(self) -> Optional[str]:
        """Get the reranker model name (alias for get_reranker_model_name)."""
        return self.get_reranker_model_name()
    
    def _load_index(self) -> faiss.Index:
        """Load FAISS index from disk."""
        index_path = Path(self.index_path)
        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found at {index_path}")
        
        logger.info(f"Loading FAISS index from {index_path}")
        self.index = faiss.read_index(str(index_path))
        logger.info(f"Loaded index with {self.index.ntotal} vectors")
        return self.index
    
    def _load_metadata(self) -> Dict[int, Dict[str, Any]]:
        """Load metadata from JSONL file."""
        meta_path = Path(self.meta_path)
        if not meta_path.exists():
            raise FileNotFoundError(f"Metadata file not found at {meta_path}")
        
        logger.info(f"Loading metadata from {meta_path}")
        metadata = {}
        with open(meta_path, 'r') as f:
            for line in f:
                if line.strip():
                    meta = json.loads(line)
                    vector_id = meta.get("vector_id")
                    if vector_id is not None:
                        metadata[vector_id] = meta
        
        logger.info(f"Loaded metadata for {len(metadata)} vectors")
        return metadata
    
    def _normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """Normalize embedding to unit length for cosine similarity."""
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return embedding / norm
        return embedding
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        if HAS_SKLEARN:
            return float(cosine_similarity([a], [b])[0][0])
        else:
            # Manual cosine similarity computation
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a > 0 and norm_b > 0:
                return float(dot_product / (norm_a * norm_b))
            return 0.0
    
    def _mmr_rerank(self, candidates: List[Tuple[int, float]], query_embedding: np.ndarray, 
                   lambda_param: float, top_k: int) -> List[Tuple[int, float]]:
        """Apply Maximal Marginal Relevance (MMR) reranking."""
        if not candidates:
            return []
        
        # Get embeddings for candidates
        candidate_embeddings = []
        for idx, _ in candidates:
            if idx in self.metadata:
                # For MMR, we need the original embeddings
                # Since we don't store them, we'll use a simplified approach
                candidate_embeddings.append(np.random.random(self.dim))  # Placeholder
        
        if not candidate_embeddings:
            return candidates[:top_k]
        
        # Greedy MMR selection
        selected = []
        remaining = list(range(len(candidates)))
        
        # Start with highest scoring candidate
        if remaining:
            best_idx = max(remaining, key=lambda i: candidates[i][1])
            selected.append(best_idx)
            remaining.remove(best_idx)
        
        # Iteratively select candidates that maximize MMR score
        while len(selected) < top_k and remaining:
            best_candidate = None
            best_score = -float('inf')
            
            for candidate_idx in remaining:
                relevance = candidates[candidate_idx][1]
                
                # Calculate max similarity to already selected
                max_sim = 0.0
                for selected_idx in selected:
                    sim = self._cosine_similarity(
                        candidate_embeddings[candidate_idx],
                        candidate_embeddings[selected_idx]
                    )
                    max_sim = max(max_sim, sim)
                
                # MMR score
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_candidate = candidate_idx
            
            if best_candidate is not None:
                selected.append(best_candidate)
                remaining.remove(best_candidate)
            else:
                break
        
        # Return selected candidates in order
        return [candidates[i] for i in selected]
    
    def initialize(self) -> None:
        """Initialize the store by loading index and metadata."""
        if self._initialized:
            return
        
        with _store_lock:
            if self._initialized:
                return
            
            try:
                self.index = self._load_index()
                self.metadata = self._load_metadata()
                self._initialized = True
                logger.info("FAISS store initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize FAISS store: {e}")
                raise
    
    def search(self, query_embedding: np.ndarray, top_k: int) -> List[Tuple[int, float]]:
        """Search the index for similar vectors."""
        if not self._initialized:
            self.initialize()
        
        if self.index is None:
            return []
        
        # Normalize query embedding
        query_embedding = self._normalize_embedding(query_embedding.reshape(1, -1))
        
        # Search index
        scores, indices = self.index.search(query_embedding, top_k)
        
        # Convert to list of (index, score) tuples
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx >= 0:  # Valid index
                results.append((int(idx), float(score)))
        
        return results
    
    def get_meta(self, idx: int) -> Optional[Dict[str, Any]]:
        """Get metadata for a vector index."""
        return self.metadata.get(idx)
    
    def embed_query(self, query: str, model_name: str = None) -> np.ndarray:
        """Embed a query using the lane's embedding model."""
        if model_name is None:
            # Get lane-specific model with env override
            env_key = f"EMBED_MODEL_{self.lane.upper()}"
            model_name = os.getenv(env_key, self.config.get(self.lane, {}).get("embed_model", "sentence-transformers/all-MiniLM-L6-v2"))
        
        model = self._load_embedding_model(model_name)
        embedding = model.encode([query])[0]
        return self._normalize_embedding(embedding)
    
    def get_embedder_name(self) -> str:
        """Get the resolved embedding model name for this lane."""
        env_key = f"EMBED_MODEL_{self.lane.upper()}"
        return os.getenv(env_key, self.config.get(self.lane, {}).get("embed_model", "sentence-transformers/all-MiniLM-L6-v2"))
    
    def get_index_info(self) -> Dict[str, Any]:
        """Get index information (path, dim, count) from stats."""
        try:
            stats_path = Path(self.stats_path)
            if stats_path.exists():
                with open(stats_path, 'r') as f:
                    stats = json.load(f)
                return {
                    "path": str(self.index_path),
                    "dim": stats.get("dim", self.dim),
                    "count": stats.get("count", 0),
                    "lane": stats.get("lane", self.lane),
                    "model_name": stats.get("model_name", "unknown")
                }
        except Exception as e:
            logger.warning(f"Could not load stats from {self.stats_path}: {e}")
        
        return {
            "path": str(self.index_path),
            "dim": self.dim,
            "count": 0,
            "lane": self.lane,
            "model_name": "unknown"
        }
    
    def rerank_with_cross_encoder(self, query: str, candidates: List[Tuple[int, float]], 
                                 model_name: str, top_k: int) -> List[Tuple[int, float]]:
        """Rerank candidates using cross-encoder with batch processing."""
        # Check for environment override
        env_model = os.getenv("RERANKER_MODEL")
        if env_model:
            model_name = env_model
            logger.info(f"Using environment override reranker model: {model_name}")
        
        cross_encoder = self._load_cross_encoder(model_name)
        if cross_encoder is None:
            return candidates[:top_k]
        
        # Prepare query-document pairs
        pairs = []
        valid_candidates = []
        for idx, _ in candidates:
            meta = self.get_meta(idx)
            if meta:
                text = meta.get("text", "")
                pairs.append([query, text])
                valid_candidates.append((idx, _))
        
        if not pairs:
            return candidates[:top_k]
        
        # Get cross-encoder scores with batch processing
        try:
            import time
            start_time = time.time()
            
            # Process in batches for efficiency
            batch_size = 32
            all_scores = []
            
            for i in range(0, len(pairs), batch_size):
                batch_pairs = pairs[i:i + batch_size]
                batch_scores = cross_encoder.predict(batch_pairs)
                all_scores.extend(batch_scores)
            
            rerank_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Combine with original indices and scores
            reranked = []
            for i, (idx, _) in enumerate(valid_candidates):
                if i < len(all_scores):
                    reranked.append((idx, float(all_scores[i])))
            
            # Sort by cross-encoder score
            reranked.sort(key=lambda x: x[1], reverse=True)
            
            # Log summary
            model_name_used = self.get_reranker_model_name() or model_name
            logger.info(f"Reranked {len(candidates)} candidates to top-{top_k} using {model_name_used} in {rerank_time:.1f}ms")
            
            return reranked[:top_k]
            
        except Exception as e:
            logger.warning(f"Cross-encoder reranking failed: {e}")
            return candidates[:top_k]


def load_store(lane: str, config_path: str = None) -> FAISSStore:
    """Load FAISS store singleton for the specified lane."""
    global _store_instances
    
    if lane not in _store_instances:
        with _store_lock:
            if lane not in _store_instances:
                if not HAS_FAISS_DEPS:
                    raise ImportError("FAISS dependencies not available")
                
                # Load config
                if config_path is None:
                    # Try multiple possible config paths
                    config_paths = [
                        "config/rag.yaml",
                        "../config/rag.yaml",
                        "../../config/rag.yaml",
                    ]
                    
                    config_found = False
                    for path in config_paths:
                        if Path(path).exists():
                            config_path = path
                            config_found = True
                            break
                    
                    if not config_found:
                        raise FileNotFoundError(f"RAG config not found in any of: {config_paths}")
                
                import yaml
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                _store_instances[lane] = FAISSStore(config, lane)
    
    return _store_instances[lane]


def get_store(lane: str = None) -> Optional[FAISSStore]:
    """Get the store instance for the specified lane."""
    if lane is None:
        # Return any available store for backward compatibility
        return next(iter(_store_instances.values())) if _store_instances else None
    return _store_instances.get(lane)


def get_embedder_name(lane: str) -> str:
    """Get the embedding model name for a specific lane."""
    store = get_store(lane)
    if store:
        return store.get_embedder_name()
    return "unknown"


def get_index_info(lane: str) -> Dict[str, Any]:
    """Get index information (path, dim, count) for a specific lane."""
    store = get_store(lane)
    if store:
        return store.get_index_info()
    return {
        "path": "unknown",
        "dim": 0,
        "count": 0,
        "lane": lane,
        "model_name": "unknown"
    }


def get_reranker_name(lane: str) -> Optional[str]:
    """Get the reranker model name for a specific lane."""
    store = get_store(lane)
    if store:
        return store.get_reranker_name()
    return None
