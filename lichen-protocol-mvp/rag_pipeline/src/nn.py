"""
Simple exact nearest neighbor implementation using NumPy.
Provides a clean interface that can be swapped for production backends later.
"""

import numpy as np
from typing import List, Tuple, Optional
from abc import ABC, abstractmethod


class NearestNeighbor(ABC):
    """Abstract interface for nearest neighbor search."""

    @abstractmethod
    def search(self, query_vector: np.ndarray, k: int) -> List[Tuple[int, float]]:
        """
        Search for k nearest neighbors.

        Args:
            query_vector: Query vector of shape (embedding_dim,)
            k: Number of neighbors to return

        Returns:
            List of (index, score) tuples, sorted by score (descending)
        """
        pass


class ExactNearestNeighbor(NearestNeighbor):
    """Exact nearest neighbor search using brute force."""

    def __init__(self, vectors: np.ndarray, metric: str = "cosine"):
        """
        Initialize with vectors and similarity metric.

        Args:
            vectors: Array of shape (n_vectors, embedding_dim)
            metric: Similarity metric ("cosine", "dot", "l2")
        """
        self.vectors = vectors.astype(np.float32)
        self.metric = metric
        self.n_vectors, self.embedding_dim = vectors.shape

        # Normalize vectors for cosine similarity
        if metric == "cosine":
            norms = np.linalg.norm(self.vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1  # Avoid division by zero
            self.vectors = self.vectors / norms

    def search(self, query_vector: np.ndarray, k: int) -> List[Tuple[int, float]]:
        """
        Search for k nearest neighbors using exact computation.

        Args:
            query_vector: Query vector of shape (embedding_dim,)
            k: Number of neighbors to return

        Returns:
            List of (index, score) tuples, sorted by score (descending)
        """
        if query_vector.shape != (self.embedding_dim,):
            raise ValueError(f"Query vector shape {query_vector.shape} doesn't match embedding_dim {self.embedding_dim}")

        query_vector = query_vector.astype(np.float32)

        if self.metric == "cosine":
            # Normalize query vector
            query_norm = np.linalg.norm(query_vector)
            if query_norm == 0:
                # Return random results for zero vector
                indices = np.random.choice(self.n_vectors, size=min(k, self.n_vectors), replace=False)
                return [(int(idx), 0.0) for idx in indices]
            query_vector = query_vector / query_norm

            # Compute cosine similarities
            similarities = np.dot(self.vectors, query_vector)

        elif self.metric == "dot":
            # Dot product similarity
            similarities = np.dot(self.vectors, query_vector)

        elif self.metric == "l2":
            # L2 distance (negative for higher-is-better ordering)
            distances = np.linalg.norm(self.vectors - query_vector, axis=1)
            similarities = -distances

        else:
            raise ValueError(f"Unsupported metric: {self.metric}")

        # Get top-k indices
        top_k_indices = np.argsort(similarities)[::-1][:k]

        return [(int(idx), float(similarities[idx])) for idx in top_k_indices]

    def get_vector(self, index: int) -> np.ndarray:
        """Get vector by index."""
        if index < 0 or index >= self.n_vectors:
            raise IndexError(f"Index {index} out of range [0, {self.n_vectors})")
        return self.vectors[index]

    def get_stats(self) -> dict:
        """Get index statistics."""
        return {
            "n_vectors": self.n_vectors,
            "embedding_dim": self.embedding_dim,
            "metric": self.metric
        }
