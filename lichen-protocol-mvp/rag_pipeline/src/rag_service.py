"""
RAG service shim that serves QueryRequest -> QueryResponse using local indices.
"""

import json
import time
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import numpy as np

from indexer import IndexBuilder
from nn import NearestNeighbor


class RagService:
    """RAG service that handles query requests using local indices."""

    def __init__(self, latency_index_dir: str, accuracy_index_dir: Optional[str] = None):
        """
        Initialize RAG service with index directories.

        Args:
            latency_index_dir: Directory containing latency index
            accuracy_index_dir: Optional directory containing accuracy index
        """
        self.latency_index_dir = latency_index_dir
        self.accuracy_index_dir = accuracy_index_dir

        # Load indices
        self.latency_nn, self.latency_metadata, self.latency_meta = self._load_index(latency_index_dir)

        if accuracy_index_dir:
            self.accuracy_nn, self.accuracy_metadata, self.accuracy_meta = self._load_index(accuracy_index_dir)
        else:
            self.accuracy_nn = self.accuracy_metadata = self.accuracy_meta = None

    def _load_index(self, index_dir: str) -> tuple:
        """Load index from directory."""
        builder = IndexBuilder({})  # Empty config for loading
        return builder.load_index(index_dir)

    def query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a query request and return response.

        Args:
            payload: QueryRequest dictionary conforming to QueryRequest.schema.json

        Returns:
            QueryResponse dictionary conforming to QueryResponse.schema.json
        """
        start_time = time.time()
        retrieve_start = None
        rerank_start = None
        synth_start = None

        # Check if RAG is enabled via environment flag
        rag_enabled = os.getenv("RAG_ENABLED", "1") == "1"
        if not rag_enabled:
            total_ms = int((time.time() - start_time) * 1000)
            return {
                "v": "1.0",
                "trace_id": payload.get("trace_id", "unknown"),
                "mode": "disabled",
                "latency_ms": total_ms,
                "retrieve_ms": 0,
                "rerank_ms": 0,
                "synth_ms": 0,
                "total_ms": total_ms,
                "results": [],
                "reason": "flags.disabled"
            }

        # Get RAG profile from environment (default "fast")
        rag_profile = os.getenv("RAG_PROFILE", "fast")
        
        # Extract query parameters
        mode = payload.get("mode", rag_profile)  # Use profile as default mode if not specified
        query_text = payload["query"]
        top_k = payload.get("top_k", 5)
        filters = payload.get("filters", {})
        include_spans = payload.get("include_spans", True)
        max_chunk_tokens = payload.get("max_chunk_tokens")

        # Select index based on mode/profile
        if mode in ["latency", "fast"]:
            nn_index = self.latency_nn
            metadata = self.latency_metadata
            index_meta = self.latency_meta
        elif mode == "accuracy" and self.accuracy_nn:
            nn_index = self.accuracy_nn
            metadata = self.accuracy_metadata
            index_meta = self.accuracy_meta
        else:
            # Fallback to latency index
            nn_index = self.latency_nn
            metadata = self.latency_metadata
            index_meta = self.latency_meta

        # Start retrieval timing
        retrieve_start = time.time()
        
        # For this MVP, we'll use a simple text-based similarity
        # In production, this would use an embedding model
        query_vector_list = self._text_to_vector(query_text, nn_index.embedding_dim)
        query_vector = np.array(query_vector_list, dtype=np.float32)

        # Apply filters to metadata
        filtered_indices = self._apply_filters(metadata, filters)

        # Search for similar vectors
        if filtered_indices:
            # Create a filtered NN index for search
            filtered_vectors = nn_index.vectors[filtered_indices]
            filtered_nn = type(nn_index)(filtered_vectors, metric=nn_index.metric)
            search_results = filtered_nn.search(query_vector, min(top_k, len(filtered_indices)))

            # End retrieval timing, start reranking timing
            retrieve_ms = int((time.time() - retrieve_start) * 1000)
            rerank_start = time.time()

            # Map back to original indices
            results = []
            for rank, (filtered_idx, score) in enumerate(search_results, 1):
                original_idx = filtered_indices[filtered_idx]
                meta = metadata[original_idx]

                # Truncate text if needed
                text = meta.get("text", "")
                if max_chunk_tokens and len(text.split()) > max_chunk_tokens:
                    words = text.split()[:max_chunk_tokens]
                    text = " ".join(words) + "..."

                result = {
                    "doc_id": meta["doc_id"],
                    "chunk_id": meta["chunk_id"],
                    "rank": rank,
                    "score": score,
                    "text": text,
                    "grounding_score": meta.get("grounding_score", 0.0)
                }

                # Add source information if available
                if "source" in meta:
                    result["source"] = meta["source"]

                # Add spans if requested and available
                if include_spans and "span" in meta:
                    result["spans"] = [meta["span"]]

                results.append(result)
            
            # End reranking timing, start synthesis timing
            rerank_ms = int((time.time() - rerank_start) * 1000)
            synth_start = time.time()
        else:
            results = []
            retrieve_ms = int((time.time() - retrieve_start) * 1000)
            rerank_start = time.time()
            rerank_ms = int((time.time() - rerank_start) * 1000)
            synth_start = time.time()

        # End synthesis timing
        synth_ms = int((time.time() - synth_start) * 1000)
        
        # Calculate total latency
        total_ms = int((time.time() - start_time) * 1000)
        
        # Calculate overall grounding score (average of top results)
        overall_grounding_score = 0.0
        if results:
            grounding_scores = [r.get("grounding_score", 0.0) for r in results]
            overall_grounding_score = sum(grounding_scores) / len(grounding_scores)

        # Build response
        response = {
            "v": "1.0",
            "trace_id": payload.get("trace_id", "unknown"),
            "mode": mode,
            "latency_ms": total_ms,  # Keep for backward compatibility
            "retrieve_ms": retrieve_ms,
            "rerank_ms": rerank_ms,
            "synth_ms": synth_ms,
            "total_ms": total_ms,
            "results": results,
            "grounding_score": overall_grounding_score
        }

        # Add warnings if any
        warnings = []
        if len(results) < top_k:
            warnings.append(f"Only {len(results)} results found (requested {top_k})")
        if mode == "accuracy" and not self.accuracy_nn:
            warnings.append("Accuracy index not available, using latency index")

        if warnings:
            response["warnings"] = warnings

        return response

    def _text_to_vector(self, text: str, embedding_dim: int) -> List[float]:
        """
        Convert text to vector (placeholder implementation).
        In production, this would use an embedding model.
        """
        # Simple hash-based vector for deterministic results
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()

        # Convert to vector of specified dimension
        vector = []
        for i in range(embedding_dim):
            byte_idx = i % len(hash_bytes)
            vector.append((hash_bytes[byte_idx] - 128) / 128.0)

        return vector

    def _apply_filters(self, metadata: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[int]:
        """
        Apply filters to metadata and return matching indices.

        Args:
            metadata: List of metadata records
            filters: Filter dictionary with doc_types, tags, etc.

        Returns:
            List of indices that match filters
        """
        if not filters:
            return list(range(len(metadata)))

        matching_indices = []

        for idx, meta in enumerate(metadata):
            match = True

            # Filter by doc_types
            if "doc_types" in filters:
                doc_type = meta.get("source", {}).get("doc_type")
                if doc_type not in filters["doc_types"]:
                    match = False

            # Filter by tags
            if "tags" in filters and match:
                meta_tags = set(meta.get("tags", []))
                filter_tags = set(filters["tags"])
                if not meta_tags.intersection(filter_tags):
                    match = False

            if match:
                matching_indices.append(idx)

        return matching_indices
