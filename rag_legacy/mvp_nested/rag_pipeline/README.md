# RAG Pipeline

Build and serve RAG indices locally with schema validation and offline testing.

## Overview

The RAG pipeline provides:
- **Index building**: Convert vectors + metadata into searchable indices
- **Query serving**: Serve QueryRequest -> QueryResponse using local indices
- **Schema validation**: Full validation against build-time and serve-time schemas
- **Offline testing**: Deterministic results for development and testing

## Architecture

```
CorpusDoc -> Chunk -> Embed -> Index -> Query
    |         |        |        |        |
    v         v        v        v        v
Schema    Schema   Schema   Schema   Schema
Validation Validation Validation Validation Validation
```

## CLI Commands

### Index Building

Build an index from vectors and metadata:

```bash
python -m rag_pipeline.cli index \
  --config rag_pipeline/configs/index_latency.json \
  --vectors artifacts/latency/vectors.npy \
  --metadata artifacts/latency/metadata.jsonl \
  --outdir artifacts/index/latency \
  --trace-id dev-idx-1
```

### Query Serving

Query the RAG service:

```bash
python -m rag_pipeline.cli query \
  --mode latency \
  --index-dir artifacts/index/latency \
  --query "when urgency rises what protocol should I use?" \
  --top-k 3 \
  --trace-id dev-q-1
```

With filters:

```bash
python -m rag_pipeline.cli query \
  --mode latency \
  --index-dir artifacts/index/latency \
  --query "protocol guidance" \
  --top-k 5 \
  --filters '{"doc_types": ["protocol"], "tags": ["entry"]}' \
  --trace-id dev-q-2
```

## Configuration

### Index Configs

- `configs/index_latency.json`: Optimized for low latency
- `configs/index_accuracy.json`: Optimized for high accuracy

Both conform to `contracts/rag_build/IndexConfig.schema.json`.

### Supported Metrics

- `cosine`: Cosine similarity (vectors normalized)
- `dot`: Dot product similarity
- `l2`: L2 distance (negative for ranking)

## Testing

Run the test suite:

```bash
pytest rag_pipeline/tests/ -v
```

Tests include:
- Index building from vectors + metadata
- Index loading and validation
- End-to-end query functionality
- Filter application
- Schema validation

## Schema Validation

All operations validate against JSON schemas:

- **Build-time**: `contracts/rag_build/IndexConfig.schema.json`
- **Serve-time**: `contracts/rag/QueryRequest.schema.json`, `contracts/rag/QueryResponse.schema.json`

Validation failures result in clear error messages with paths and reasons.

## Implementation Details

### Nearest Neighbor Search

Uses exact (brute-force) search with NumPy for deterministic results:

- Cosine similarity with vector normalization
- Dot product similarity
- L2 distance with negative scoring

### RAG Service

- Loads indices on initialization
- Supports both latency and accuracy modes
- Applies filters before ranking
- Returns structured QueryResponse

### Offline Operation

- No network calls required
- Deterministic hash-based embeddings for testing
- All artifacts stored locally
- Fast execution (< 15s for test suite)

## File Structure

```
rag_pipeline/
├── src/
│   ├── indexer.py          # Index building
│   ├── nn.py               # Nearest neighbor search
│   └── rag_service.py      # Query serving
├── configs/
│   ├── index_latency.json  # Latency-optimized config
│   └── index_accuracy.json # Accuracy-optimized config
├── tests/
│   ├── test_index_build.py # Index building tests
│   └── test_query_e2e.py   # End-to-end query tests
└── cli.py                  # Command-line interface
```

## Future Extensions

- Production backends (FAISS, pgvector, Qdrant)
- Cross-encoder reranking
- Embedding model integration
- Distributed indexing
- Real-time index updates
