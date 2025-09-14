"""
End-to-end test for RAG query functionality.
"""

import json
import tempfile
import shutil
from pathlib import Path
import numpy as np
import pytest

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from indexer import IndexBuilder
from rag_service import RagService


def test_query_e2e():
    """Test end-to-end query functionality."""
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test vectors
        vectors = np.random.rand(3, 4).astype(np.float32)
        vectors_path = temp_path / "vectors.npy"
        np.save(vectors_path, vectors)

        # Create test metadata with text
        metadata = [
            {
                "doc_id": "doc-entry-room",
                "chunk_id": "chunk-1",
                "text": "The entry room receives first words, reflects clearly, sets pace, and invites consent.",
                "token_count": 15,
                "span": {"start": 0, "end": 85},
                "section": "introduction",
                "tags": ["entry", "consent"],
                "source": {
                    "doc_type": "protocol",
                    "title": "Entry Room Protocol",
                    "url": "https://lichen.system/protocols/entry"
                }
            },
            {
                "doc_id": "doc-diagnostic-room",
                "chunk_id": "chunk-1",
                "text": "The diagnostic room captures system state, assesses readiness, and provides clear feedback.",
                "token_count": 16,
                "span": {"start": 0, "end": 95},
                "section": "introduction",
                "tags": ["diagnostic", "readiness"],
                "source": {
                    "doc_type": "protocol",
                    "title": "Diagnostic Room Protocol",
                    "url": "https://lichen.system/protocols/diagnostic"
                }
            },
            {
                "doc_id": "doc-memory-room",
                "chunk_id": "chunk-1",
                "text": "The memory room stores and retrieves context, maintaining session continuity across interactions.",
                "token_count": 17,
                "span": {"start": 0, "end": 105},
                "section": "introduction",
                "tags": ["memory", "context"],
                "source": {
                    "doc_type": "protocol",
                    "title": "Memory Room Protocol",
                    "url": "https://lichen.system/protocols/memory"
                }
            }
        ]

        metadata_path = temp_path / "metadata.jsonl"
        with open(metadata_path, 'w') as f:
            for record in metadata:
                f.write(json.dumps(record) + '\n')

        # Create index config
        config = {
            "index_id": "test-index",
            "mode": "latency",
            "ann": {
                "backend": "faiss",
                "metric": "cosine",
                "params": {"kind": "bruteforce"}
            },
            "reranker": None,
            "metadata_fields": ["doc_type", "tags", "section"],
            "limits": {"top_k_max": 10, "p95_target_ms": 150},
            "created_at": "2025-09-07T00:00:00Z"
        }

        # Build index
        builder = IndexBuilder(config)
        index_dir = temp_path / "index"
        builder.build_index(
            vectors_path=str(vectors_path),
            metadata_path=str(metadata_path),
            output_dir=str(index_dir),
            trace_id="test-trace"
        )

        # Initialize RAG service
        rag_service = RagService(latency_index_dir=str(index_dir))

        # Test query
        query_request = {
            "v": "1.0",
            "trace_id": "test-query-1",
            "query": "when urgency rises what protocol should I use?",
            "mode": "latency",
            "top_k": 3
        }

        response = rag_service.query(query_request)

        # Validate response structure
        assert "v" in response
        assert "trace_id" in response
        assert "mode" in response
        assert "latency_ms" in response
        assert "results" in response

        assert response["v"] == "1.0"
        assert response["trace_id"] == "test-query-1"
        assert response["mode"] == "latency"
        assert isinstance(response["latency_ms"], int)
        assert response["latency_ms"] >= 0

        # Validate results
        results = response["results"]
        assert isinstance(results, list)
        assert len(results) <= 3  # top_k

        # Check result structure
        for i, result in enumerate(results):
            assert "doc_id" in result
            assert "chunk_id" in result
            assert "rank" in result
            assert "score" in result
            assert "text" in result

            assert result["rank"] == i + 1
            assert isinstance(result["score"], (int, float))
            assert isinstance(result["text"], str)
            assert len(result["text"]) > 0

        # Check scores are monotonically non-increasing
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]["score"] >= results[i + 1]["score"]


def test_query_with_filters():
    """Test query with filters."""
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test vectors
        vectors = np.random.rand(2, 3).astype(np.float32)
        vectors_path = temp_path / "vectors.npy"
        np.save(vectors_path, vectors)

        # Create test metadata with different doc_types
        metadata = [
            {
                "doc_id": "doc-protocol-1",
                "chunk_id": "chunk-1",
                "text": "Protocol text 1",
                "token_count": 3,
                "span": {"start": 0, "end": 15},
                "tags": ["protocol"],
                "source": {"doc_type": "protocol", "title": "Protocol 1"}
            },
            {
                "doc_id": "doc-essay-1",
                "chunk_id": "chunk-1",
                "text": "Essay text 1",
                "token_count": 3,
                "span": {"start": 0, "end": 12},
                "tags": ["essay"],
                "source": {"doc_type": "essay", "title": "Essay 1"}
            }
        ]

        metadata_path = temp_path / "metadata.jsonl"
        with open(metadata_path, 'w') as f:
            for record in metadata:
                f.write(json.dumps(record) + '\n')

        # Create index config
        config = {
            "index_id": "test-index",
            "mode": "latency",
            "ann": {
                "backend": "faiss",
                "metric": "cosine",
                "params": {"kind": "bruteforce"}
            },
            "reranker": None,
            "metadata_fields": ["doc_type", "tags"],
            "limits": {"top_k_max": 10},
            "created_at": "2025-09-07T00:00:00Z"
        }

        # Build index
        builder = IndexBuilder(config)
        index_dir = temp_path / "index"
        builder.build_index(
            vectors_path=str(vectors_path),
            metadata_path=str(metadata_path),
            output_dir=str(index_dir),
            trace_id="test-trace"
        )

        # Initialize RAG service
        rag_service = RagService(latency_index_dir=str(index_dir))

        # Test query with doc_type filter
        query_request = {
            "v": "1.0",
            "trace_id": "test-query-filter",
            "query": "test query",
            "mode": "latency",
            "top_k": 5,
            "filters": {
                "doc_types": ["protocol"]
            }
        }

        response = rag_service.query(query_request)

        # Should only return protocol results
        for result in response["results"]:
            # Find the corresponding metadata
            for meta in metadata:
                if meta["doc_id"] == result["doc_id"]:
                    assert meta["source"]["doc_type"] == "protocol"
                    break
