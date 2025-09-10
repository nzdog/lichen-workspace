"""
Index builder that consumes IndexConfig + vectors/metadata to build/update a local index.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List
import numpy as np

from nn import ExactNearestNeighbor


class IndexBuilder:
    """Builds and manages search indices from vectors and metadata."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize with IndexConfig.

        Args:
            config: IndexConfig dictionary conforming to IndexConfig.schema.json
        """
        self.config = config
        self.index_id = config.get("index_id", "unknown")
        self.mode = config.get("mode", "latency")
        self.ann_config = config.get("ann", {"backend": "faiss", "metric": "cosine", "params": {}})
        self.metadata_fields = config.get("metadata_fields", [])
        self.limits = config.get("limits", {})

    def build_index(self, vectors_path: str, metadata_path: str, output_dir: str, trace_id: str) -> Dict[str, Any]:
        """
        Build index from vectors and metadata files.

        Args:
            vectors_path: Path to .npy file containing vectors
            metadata_path: Path to .jsonl file containing metadata
            output_dir: Directory to write index artifacts
            trace_id: Trace ID for logging

        Returns:
            Dictionary with build statistics
        """
        start_time = time.time()

        # Load vectors
        vectors = np.load(vectors_path)
        print(f"[{trace_id}] Loaded vectors: {vectors.shape}")

        # Load metadata
        metadata = []
        with open(metadata_path, 'r') as f:
            for line in f:
                if line.strip():
                    metadata.append(json.loads(line))

        print(f"[{trace_id}] Loaded metadata: {len(metadata)} records")

        if len(metadata) != vectors.shape[0]:
            raise ValueError(f"Vector count {vectors.shape[0]} doesn't match metadata count {len(metadata)}")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Build nearest neighbor index
        nn_index = ExactNearestNeighbor(vectors, metric=self.ann_config["metric"])

        # Save vectors (possibly normalized)
        vectors_output_path = output_path / "vectors.npy"
        np.save(vectors_output_path, nn_index.vectors)

        # Save metadata
        metadata_output_path = output_path / "meta.jsonl"
        with open(metadata_output_path, 'w') as f:
            for record in metadata:
                f.write(json.dumps(record) + '\n')

        # Save index metadata
        index_meta = {
            "index_id": self.index_id,
            "mode": self.mode,
            "metric": self.ann_config["metric"],
            "backend": self.ann_config["backend"],
            "count": len(metadata),
            "embedding_dim": vectors.shape[1],
            "metadata_fields": self.metadata_fields,
            "limits": self.limits,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "trace_id": trace_id
        }

        meta_output_path = output_path / "index.meta.json"
        with open(meta_output_path, 'w') as f:
            json.dump(index_meta, f, indent=2)

        build_time = time.time() - start_time

        stats = {
            "trace_id": trace_id,
            "index_id": self.index_id,
            "mode": self.mode,
            "vectors_shape": vectors.shape,
            "metadata_count": len(metadata),
            "build_time_ms": int(build_time * 1000),
            "output_dir": str(output_path),
            "files_created": [
                str(vectors_output_path),
                str(metadata_output_path),
                str(meta_output_path)
            ]
        }

        print(f"[{trace_id}] Index built successfully in {build_time:.2f}s")
        print(f"[{trace_id}] Files created: {len(stats['files_created'])}")

        return stats

    def load_index(self, index_dir: str) -> tuple:
        """
        Load an existing index from directory.

        Args:
            index_dir: Directory containing index artifacts

        Returns:
            Tuple of (nn_index, metadata, index_meta)
        """
        index_path = Path(index_dir)

        # Load index metadata
        meta_path = index_path / "index.meta.json"
        with open(meta_path, 'r') as f:
            index_meta = json.load(f)

        # Load vectors
        vectors_path = index_path / "vectors.npy"
        vectors = np.load(vectors_path)

        # Load metadata
        metadata_path = index_path / "meta.jsonl"
        metadata = []
        with open(metadata_path, 'r') as f:
            for line in f:
                if line.strip():
                    metadata.append(json.loads(line))

        # Create NN index
        nn_index = ExactNearestNeighbor(vectors, metric=index_meta["metric"])

        return nn_index, metadata, index_meta
