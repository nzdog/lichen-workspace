"""
CLI for RAG pipeline operations.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from indexer import IndexBuilder
from rag_service import RagService
from embedders import _select_embedder


def load_and_validate_schema(file_path: str, schema_path: str) -> Dict[str, Any]:
    """Load and validate JSON against schema."""
    try:
        from jsonschema import Draft202012Validator

        # Load data
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Load schema
        with open(schema_path, 'r') as f:
            schema = json.load(f)

        # Validate
        validator = Draft202012Validator(schema)
        validator.validate(data)

        return data
    except Exception as e:
        print(f"❌ Schema validation failed for {file_path}: {e}")
        sys.exit(1)


def index_command(args):
    """Build index from vectors and metadata."""
    print(f"🔨 Building index with trace_id: {args.trace_id}")

    # Validate IndexConfig
    config = load_and_validate_schema(
        args.config,
        "contracts/rag_build/IndexConfig.schema.json"
    )

    # Build index
    builder = IndexBuilder(config)
    stats = builder.build_index(
        vectors_path=args.vectors,
        metadata_path=args.metadata,
        output_dir=args.outdir,
        trace_id=args.trace_id
    )

    print(f"✅ Index built successfully")
    print(f"   Index ID: {stats['index_id']}")
    print(f"   Mode: {stats['mode']}")
    print(f"   Vectors: {stats['vectors_shape']}")
    print(f"   Metadata: {stats['metadata_count']} records")
    print(f"   Build time: {stats['build_time_ms']}ms")
    print(f"   Output: {stats['output_dir']}")


def embed_command(args):
    """Generate embeddings from chunks using configured embedder."""
    print(f"🔮 Generating embeddings with trace_id: {args.trace_id}")

    # Validate EmbeddingJob config
    config = load_and_validate_schema(
        args.job,
        "contracts/rag_build/EmbeddingJob.schema.json"
    )

    # Load chunks
    chunks = []
    with open(args.chunks, 'r') as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))

    print(f"[{args.trace_id}] Loaded {len(chunks)} chunks")

    # Extract texts for embedding
    texts = [chunk["text"] for chunk in chunks]

    # Select embedder based on environment
    embedder = _select_embedder()
    embedder_type = type(embedder).__name__
    print(f"[{args.trace_id}] Using embedder: {embedder_type}")

    # Generate embeddings
    import time
    start_time = time.time()

    vectors = embedder.embed(
        texts,
        dim=config["embedding_dim"],
        normalize=config["normalize"],
        precision=config["precision"],
        seed=config.get("seed")
    )

    embed_time = time.time() - start_time

    # Create output directory
    output_dir = Path(config["output_uri"])
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save vectors
    vectors_path = output_dir / "vectors.npy"
    import numpy as np
    np.save(vectors_path, vectors)

    # Save metadata (reuse chunk data)
    metadata_path = output_dir / "metadata.jsonl"
    with open(metadata_path, 'w') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + '\n')

    # Save job metadata
    job_meta = {
        "job_id": config["job_id"],
        "embed_model": config["embed_model"],
        "embedding_dim": config["embedding_dim"],
        "normalize": config["normalize"],
        "precision": config["precision"],
        "seed": config.get("seed"),
        "embedder_type": embedder_type,
        "chunk_count": len(chunks),
        "embed_time_ms": int(embed_time * 1000),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "trace_id": args.trace_id
    }

    meta_path = output_dir / "embedding.meta.json"
    with open(meta_path, 'w') as f:
        json.dump(job_meta, f, indent=2)

    print(f"✅ Embeddings generated successfully")
    print(f"   Job ID: {config['job_id']}")
    print(f"   Embedder: {embedder_type}")
    print(f"   Vectors: {vectors.shape}")
    print(f"   Embed time: {embed_time:.2f}s")
    print(f"   Output: {output_dir}")


def query_command(args):
    """Query the RAG service."""
    print(f"🔍 Querying with trace_id: {args.trace_id}")

    # Build QueryRequest
    query_request = {
        "v": "1.0",
        "trace_id": args.trace_id,
        "query": args.query,
        "mode": args.mode,
        "top_k": args.top_k
    }

    # Add filters if provided
    if args.filters:
        query_request["filters"] = json.loads(args.filters)

    # Validate QueryRequest
    try:
        from jsonschema import Draft202012Validator

        with open("contracts/rag/QueryRequest.schema.json", 'r') as f:
            schema = json.load(f)

        validator = Draft202012Validator(schema)
        validator.validate(query_request)
    except Exception as e:
        print(f"❌ QueryRequest validation failed: {e}")
        sys.exit(1)

    # Initialize RAG service
    rag_service = RagService(
        latency_index_dir=args.index_dir,
        accuracy_index_dir=args.accuracy_index_dir
    )

    # Execute query
    response = rag_service.query(query_request)

    # Validate QueryResponse
    try:
        with open("contracts/rag/QueryResponse.schema.json", 'r') as f:
            schema = json.load(f)

        validator = Draft202012Validator(schema)
        validator.validate(response)
    except Exception as e:
        print(f"❌ QueryResponse validation failed: {e}")
        sys.exit(1)

    # Print results
    print(f"✅ Query completed in {response['latency_ms']}ms")
    print(f"   Mode: {response['mode']}")
    print(f"   Results: {len(response['results'])}")

    if response.get("warnings"):
        print(f"   Warnings: {', '.join(response['warnings'])}")

    print("\n📋 Results:")
    print("-" * 80)

    for result in response["results"]:
        print(f"Rank {result['rank']}: {result['score']:.4f}")
        print(f"  Doc: {result['doc_id']} | Chunk: {result['chunk_id']}")
        if "source" in result:
            source = result["source"]
            print(f"  Source: {source.get('doc_type', 'unknown')} - {source.get('title', 'untitled')}")
        print(f"  Text: {result['text'][:140]}{'...' if len(result['text']) > 140 else ''}")
        print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="RAG Pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Index command
    index_parser = subparsers.add_parser("index", help="Build index from vectors and metadata")
    index_parser.add_argument("--config", required=True, help="IndexConfig JSON file")
    index_parser.add_argument("--vectors", required=True, help="Vectors .npy file")
    index_parser.add_argument("--metadata", required=True, help="Metadata .jsonl file")
    index_parser.add_argument("--outdir", required=True, help="Output directory")
    index_parser.add_argument("--trace-id", required=True, help="Trace ID")
    index_parser.set_defaults(func=index_command)

    # Embed command
    embed_parser = subparsers.add_parser("embed", help="Generate embeddings from chunks")
    embed_parser.add_argument("--job", required=True, help="EmbeddingJob JSON file")
    embed_parser.add_argument("--chunks", required=True, help="Chunks .jsonl file")
    embed_parser.add_argument("--trace-id", required=True, help="Trace ID")
    embed_parser.set_defaults(func=embed_command)

    # Query command
    query_parser = subparsers.add_parser("query", help="Query the RAG service")
    query_parser.add_argument("--mode", required=True, choices=["latency", "accuracy"], help="Query mode")
    query_parser.add_argument("--index-dir", required=True, help="Index directory")
    query_parser.add_argument("--accuracy-index-dir", help="Accuracy index directory (optional)")
    query_parser.add_argument("--query", required=True, help="Query text")
    query_parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    query_parser.add_argument("--filters", help="JSON filters (optional)")
    query_parser.add_argument("--trace-id", required=True, help="Trace ID")
    query_parser.set_defaults(func=query_command)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
