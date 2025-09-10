"""Sentence-BERT embedding backend."""

import os
from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from .base import EmbeddingBackend


class SBERTEmbedder(EmbeddingBackend):
    """Sentence-BERT embedding backend using all-MiniLM-L6-v2."""
    
    def __init__(
        self, 
        model_name: str = "all-MiniLM-L6-v2",
        cache_dir: Optional[str] = None
    ):
        """
        Initialize SBERT embedder.
        
        Args:
            model_name: HuggingFace model name
            cache_dir: Directory to cache models
        """
        self.model_name = model_name
        self.cache_dir = cache_dir or os.path.join(os.path.expanduser("~"), ".cache", "sentence_transformers")
        
        # Lazy load model
        self._model: Optional[SentenceTransformer] = None
    
    @property
    def model(self) -> SentenceTransformer:
        """Get or load the model."""
        if self._model is None:
            self._model = SentenceTransformer(
                self.model_name,
                cache_folder=self.cache_dir
            )
        return self._model
    
    def embed_text(self, text: str) -> List[float]:
        """Embed a single text."""
        embedding = self.model.encode([text])
        return embedding[0].tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        embeddings = self.model.encode(texts)
        return [embedding.tolist() for embedding in embeddings]
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()
    
    @property
    def name(self) -> str:
        """Get backend name."""
        return f"sbert-{self.model_name}"

