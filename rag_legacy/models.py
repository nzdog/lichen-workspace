"""
Cached singleton models for embedding and cross-encoding.

Provides thread-safe, cached access to embedding models and cross-encoders
with offline support and proper environment variable handling.
"""

import os
import threading
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Global cache with thread safety
_model_cache: Dict[str, Any] = {}
_cache_lock = threading.Lock()


@dataclass
class EmbeddingModel:
    """Wrapper for embedding model with metadata."""
    model: Any
    model_name: str
    dimension: int
    is_cached: bool = False


def _setup_offline_mode():
    """Setup offline mode for Hugging Face libraries."""
    offline_vars = {
        'HF_HUB_OFFLINE': '1',
        'TRANSFORMERS_OFFLINE': '1',
        'SENTENCE_TRANSFORMERS_HOME': os.path.expanduser(os.getenv('SENTENCE_TRANSFORMERS_HOME', '~/.cache/sentence_transformers'))
    }
    
    for var, value in offline_vars.items():
        if not os.getenv(var):
            os.environ[var] = value
            logger.debug(f"Set {var}={value}")


def get_embedder(model_name: str) -> EmbeddingModel:
    """
    Get cached embedding model singleton.
    
    Args:
        model_name: Model name (e.g., 'sentence-transformers/all-MiniLM-L6-v2')
        
    Returns:
        EmbeddingModel wrapper with model and metadata
        
    Raises:
        ImportError: If sentence-transformers not available
        RuntimeError: If model loading fails
    """
    global _model_cache, _cache_lock
    
    # Setup offline mode
    _setup_offline_mode()
    
    with _cache_lock:
        cache_key = f"embedder:{model_name}"
        
        if cache_key in _model_cache:
            cached_model = _model_cache[cache_key]
            cached_model.is_cached = True
            logger.debug(f"Cache hit for embedder: {model_name}")
            return cached_model
        
        logger.info(f"Loading embedder: {model_name}")
        
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError("sentence-transformers not available. Install with: pip install sentence-transformers") from e
        
        try:
            # Load model with offline support
            model = SentenceTransformer(model_name)
            
            # Get dimension
            test_embedding = model.encode(["test"])
            dimension = len(test_embedding[0])
            
            # Create wrapper
            embedding_model = EmbeddingModel(
                model=model,
                model_name=model_name,
                dimension=dimension,
                is_cached=False
            )
            
            # Cache it
            _model_cache[cache_key] = embedding_model
            
            logger.info(f"Loaded embedder: {model_name} (dim={dimension})")
            return embedding_model
            
        except Exception as e:
            raise RuntimeError(f"Failed to load embedder {model_name}: {e}") from e


def get_cross_encoder(model_name: str) -> Optional[Any]:
    """
    Get cached cross-encoder singleton (optional).
    
    Args:
        model_name: Cross-encoder model name
        
    Returns:
        Cross-encoder model or None if not available
        
    Raises:
        ImportError: If sentence-transformers not available
    """
    global _model_cache, _cache_lock
    
    if not model_name:
        return None
    
    # Setup offline mode
    _setup_offline_mode()
    
    with _cache_lock:
        cache_key = f"cross_encoder:{model_name}"
        
        if cache_key in _model_cache:
            logger.debug(f"Cache hit for cross-encoder: {model_name}")
            return _model_cache[cache_key]
        
        logger.info(f"Loading cross-encoder: {model_name}")
        
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as e:
            raise ImportError("sentence-transformers not available. Install with: pip install sentence-transformers") from e
        
        try:
            model = CrossEncoder(model_name)
            _model_cache[cache_key] = model
            logger.info(f"Loaded cross-encoder: {model_name}")
            return model
            
        except Exception as e:
            logger.warning(f"Failed to load cross-encoder {model_name}: {e}")
            return None


def clear_cache():
    """Clear the model cache (useful for testing)."""
    global _model_cache, _cache_lock
    
    with _cache_lock:
        _model_cache.clear()
        logger.info("Model cache cleared")


def get_cache_info() -> Dict[str, Any]:
    """Get information about cached models."""
    global _model_cache
    
    return {
        "cached_models": list(_model_cache.keys()),
        "cache_size": len(_model_cache),
        "embedders": [k for k in _model_cache.keys() if k.startswith("embedder:")],
        "cross_encoders": [k for k in _model_cache.keys() if k.startswith("cross_encoder:")]
    }
