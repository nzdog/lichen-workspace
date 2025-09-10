"""
Test index building functionality.
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


def test_index_build():
    """Test building an index from vectors and metadata."""
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test vectors
        vectors = np.random.rand(3, 4).astype(np.float32)
        vectors_path = temp_path / "vectors.npy"
        np.save(vectors_path, vectors)

        # Create test metadata
        metadata = [
            {
                "doc_id": "doc-1",
                "chunk_id": "chunk-1",
                "text": "Test text 1",
                "token_count": 2,
                "span": {"start": 0, "end": 10},
                "tags": ["test"]
            },
            {
                "doc_id": "doc-2",
                "chunk_id": "chunk-1",
                "text": "Test text 2",
                "token_count": 2,
                "span": {"start": 0, "end": 10},
                "tags": ["test"]
            },
            {
                "doc_id": "doc-3",
                "chunk_id": "chunk-1",
                "text": "Test text 3",
                "token_count": 2,
                "span": {"start": 0, "end": 10},
                "tags": ["test"]
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
        output_dir = temp_path / "index"
        stats = builder.build_index(
            vectors_path=str(vectors_path),
            metadata_path=str(metadata_path),
            output_dir=str(output_dir),
            trace_id="test-trace"
        )

        # Verify output files exist
        assert (output_dir / "vectors.npy").exists()
        assert (output_dir / "meta.jsonl").exists()
        assert (output_dir / "index.meta.json").exists()

        # Verify index metadata
        with open(output_dir / "index.meta.json", 'r') as f:
            index_meta = json.load(f)

        assert index_meta["index_id"] == "test-index"
        assert index_meta["mode"] == "latency"
        assert index_meta["count"] == 3
        assert index_meta["embedding_dim"] == 4
        assert index_meta["metric"] == "cosine"

        # Verify vectors were saved
        saved_vectors = np.load(output_dir / "vectors.npy")
        assert saved_vectors.shape == (3, 4)

        # Verify metadata was saved
        saved_metadata = []
        with open(output_dir / "meta.jsonl", 'r') as f:
            for line in f:
                if line.strip():
                    saved_metadata.append(json.loads(line))

        assert len(saved_metadata) == 3
        assert saved_metadata[0]["doc_id"] == "doc-1"

        # Verify stats
        assert stats["vectors_shape"] == (3, 4)
        assert stats["metadata_count"] == 3
        assert stats["index_id"] == "test-index"
        assert len(stats["files_created"]) == 3


def test_index_load():
    """Test loading an existing index."""
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test vectors
        vectors = np.random.rand(2, 3).astype(np.float32)
        vectors_path = temp_path / "vectors.npy"
        np.save(vectors_path, vectors)

        # Create test metadata
        metadata = [
            {
                "doc_id": "doc-1",
                "chunk_id": "chunk-1",
                "text": "Test text 1",
                "token_count": 2,
                "span": {"start": 0, "end": 10}
            },
            {
                "doc_id": "doc-2",
                "chunk_id": "chunk-1",
                "text": "Test text 2",
                "token_count": 2,
                "span": {"start": 0, "end": 10}
            }
        ]

        metadata_path = temp_path / "meta.jsonl"
        with open(metadata_path, 'w') as f:
            for record in metadata:
                f.write(json.dumps(record) + '\n')

        # Create index metadata
        index_meta = {
            "index_id": "test-index",
            "mode": "latency",
            "metric": "cosine",
            "backend": "faiss",
            "count": 2,
            "embedding_dim": 3,
            "metadata_fields": ["doc_type", "tags"],
            "limits": {"top_k_max": 10},
            "created_at": "2025-09-07T00:00:00Z"
        }

        meta_path = temp_path / "index.meta.json"
        with open(meta_path, 'w') as f:
            json.dump(index_meta, f)

        # Test loading
        builder = IndexBuilder({})
        nn_index, loaded_metadata, loaded_meta = builder.load_index(str(temp_path))

        # Verify loaded data
        assert nn_index.n_vectors == 2
        assert nn_index.embedding_dim == 3
        assert nn_index.metric == "cosine"

        assert len(loaded_metadata) == 2
        assert loaded_metadata[0]["doc_id"] == "doc-1"

        assert loaded_meta["index_id"] == "test-index"
        assert loaded_meta["count"] == 2
