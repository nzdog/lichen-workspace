"""OpenAI embedding backend."""

import os
import time
from typing import List, Optional

import numpy as np
import openai
from openai import OpenAI
from dotenv import load_dotenv

from .base import EmbeddingBackend


class OpenAIEmbedder(EmbeddingBackend):
    """OpenAI embedding backend using text-embedding-3-large."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-large",
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize OpenAI embedder.
        
        Args:
            api_key: OpenAI API key (uses env var if None)
            model: Model name
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Load environment variables
        load_dotenv()
        
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not provided and OPENAI_API_KEY env var not set")
        
        self.client = OpenAI(api_key=api_key)
        
        # Model dimensions
        self._dimension = 3072 if "3-large" in model else 1536
    
    def embed_text(self, text: str) -> List[float]:
        """Embed a single text."""
        return self.embed_batch([text])[0]
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of texts with retry logic.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts
                )
                
                embeddings = []
                for item in response.data:
                    embeddings.append(item.embedding)
                
                return embeddings
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"Failed to embed texts after {self.max_retries} attempts: {e}")
                
                print(f"Embedding attempt {attempt + 1} failed: {e}. Retrying in {self.retry_delay}s...")
                time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
        
        return []
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension
    
    @property
    def name(self) -> str:
        """Get backend name."""
        return f"openai-{self.model}"

