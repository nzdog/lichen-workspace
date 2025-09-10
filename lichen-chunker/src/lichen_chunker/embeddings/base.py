"""Base embedding backend interface."""

from abc import ABC, abstractmethod
from typing import List, Optional


class EmbeddingBackend(ABC):
    """Abstract base class for embedding backends."""
    
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """
        Embed a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Get embedding dimension."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get backend name."""
        pass

