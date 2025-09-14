"""
Embedding implementations for RAG pipeline.
Supports both deterministic stub embeddings and OpenAI embeddings.
"""

from __future__ import annotations
import os
import hashlib
import numpy as np
from typing import Iterable, List, Optional


class BaseEmbedder:
    """Base class for text embedders."""

    def embed(self, texts: List[str], *, dim: int, normalize: bool, precision: str, seed: Optional[int]) -> np.ndarray:
        """
        Embed a list of texts.

        Args:
            texts: List of text strings to embed
            dim: Embedding dimension
            normalize: Whether to normalize embeddings
            precision: Precision type (fp32, fp16, bf16)
            seed: Random seed for reproducibility

        Returns:
            Array of shape (len(texts), dim) with embeddings
        """
        raise NotImplementedError


class StubEmbedder(BaseEmbedder):
    """Deterministic hash-based embeddings for tests/offline runs."""

    def embed(self, texts: List[str], *, dim: int, normalize: bool, precision: str, seed: Optional[int]) -> np.ndarray:
        """
        Generate deterministic embeddings using hash-based approach.

        Args:
            texts: List of text strings to embed
            dim: Embedding dimension
            normalize: Whether to normalize embeddings
            precision: Precision type (fp32, fp16, bf16)
            seed: Random seed for reproducibility

        Returns:
            Array of shape (len(texts), dim) with deterministic embeddings
        """
        rng_seed = (seed or 13) & 0xFFFFFFFF
        out = np.empty((len(texts), dim), dtype=np.float32)

        for i, t in enumerate(texts):
            h = hashlib.sha256(f"{rng_seed}:{t}".encode("utf-8")).digest()
            vec = np.frombuffer((h * ((dim // 32) + 1))[:dim], dtype=np.uint8).astype(np.float32)
            # center to mean ~0, scale to [-0.5,0.5]
            vec = (vec - 127.5) / 255.0
            out[i] = vec

        if normalize:
            norms = np.linalg.norm(out, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            out = out / norms

        if precision == "fp16":
            out = out.astype(np.float16)
        elif precision == "bf16":
            out = out.astype(np.float32)  # numpy bfloat16 not universally supported; keep fp32

        return out


class OpenAIEmbedder(BaseEmbedder):
    """
    Uses OpenAI Embeddings when RAG_REAL_EMBED=1.
    Expects OPENAI_API_KEY in env. Optional OPENAI_BASE_URL to override endpoint.
    """

    MODEL_DIMS = {
        "text-embedding-3-large": 3072,
        "text-embedding-3-small": 1536
    }

    def __init__(self):
        """Initialize OpenAI client with lazy import."""
        # Lazy import to avoid hard dependency in tests/CI
        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:
            raise RuntimeError("openai package not installed; cannot use OpenAIEmbedder") from e

        base_url = os.getenv("OPENAI_BASE_URL")
        self.client = OpenAI(base_url=base_url) if base_url else OpenAI()

    def embed(self, texts: List[str], *, dim: int, normalize: bool, precision: str, seed: Optional[int]) -> np.ndarray:
        """
        Generate embeddings using OpenAI API.

        Args:
            texts: List of text strings to embed
            dim: Embedding dimension
            normalize: Whether to normalize embeddings
            precision: Precision type (fp32, fp16, bf16)
            seed: Random seed for reproducibility (ignored for OpenAI)

        Returns:
            Array of shape (len(texts), dim) with OpenAI embeddings
        """
        # Retrieve model from env or default
        model = os.getenv("RAG_OPENAI_EMBED_MODEL", "text-embedding-3-large")

        if model in self.MODEL_DIMS and self.MODEL_DIMS[model] != dim:
            raise ValueError(f"Embedding dim mismatch: model {model} -> {self.MODEL_DIMS[model]}, but job dim={dim}")

        # Call API in batches
        from math import ceil
        import time

        batch_size = int(os.getenv("RAG_OPENAI_EMBED_BATCH", "128"))
        out = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            # Note: OpenAI API expects list[str] as 'input'
            resp = self.client.embeddings.create(model=model, input=batch, dimensions=None)
            mat = np.array([d.embedding for d in resp.data], dtype=np.float32)
            out.append(mat)

            # Simple throttle to be polite; configurable
            time.sleep(float(os.getenv("RAG_OPENAI_EMBED_SLEEP", "0.0")))

        arr = np.vstack(out)

        if normalize:
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            arr = arr / norms

        if precision == "fp16":
            arr = arr.astype(np.float16)
        elif precision == "bf16":
            arr = arr.astype(np.float32)

        return arr


def _select_embedder() -> BaseEmbedder:
    """
    Select embedder based on environment variables.

    Returns:
        StubEmbedder by default, OpenAIEmbedder if RAG_REAL_EMBED=1 and API key is set
    """
    use_real_embed = os.getenv("RAG_REAL_EMBED") == "1"
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))

    if use_real_embed and has_api_key:
        try:
            return OpenAIEmbedder()
        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize OpenAI embedder: {e}")
            print("   Falling back to StubEmbedder")
            return StubEmbedder()
    else:
        return StubEmbedder()
