# MVP4 – Lichen Protocol Build Canon & Contracts

This repo contains the **MVP4 build canon**, contracts, and schemas for the Lichen Protocol system.

## 📂 Structure

- **build_canon/** – Canon-style governance protocols (Rooms, Orchestration, Gates, Diagnostics & Memory).
- **contracts/**
  - **services/** – Machine-readable contracts for diagnostics and memory.
  - **rooms/** – Contracts for PRA rooms.
  - **gates/** – Contracts for output gates.
  - **rag/** – RAG boundary schemas for query/response/error/telemetry.
  - **rag_build/** – RAG build-time schemas for corpus/chunks/embeddings/indexing.
  - **schema/** – JSON Schemas for validation.
  - **types/** – Auto-generated TypeScript definitions (from schemas).
- **package.json** – Validation & type generation scripts.

## 🛠️ Setup

Clone the repo and install dev dependencies:

```bash
git clone git@github.com:nzdog/MVP4.git
cd MVP4
npm install
```

## 📋 Contracts

### Contracts → RAG

The RAG (Retrieval-Augmented Generation) boundary schemas define the interfaces for query processing:

- `contracts/rag/QueryRequest.schema.json` - Query request format
- `contracts/rag/QueryResponse.schema.json` - Query response format
- `contracts/rag/Error.schema.json` - Error response format
- `contracts/rag/TelemetryEvent.schema.json` - Telemetry event format

**Validation:**
```bash
python scripts/validate.py
python scripts/validate_cross_contracts.py
python scripts/validate_dependencies.py
pytest -q
```

**Note:** RAG has no cross-dependencies yet; validation scripts exit cleanly.

### Contracts → RAG Build

The RAG build-time schemas define the interfaces for corpus processing and indexing:

- `contracts/rag_build/CorpusDoc.schema.json` - Document corpus format
- `contracts/rag_build/Chunk.schema.json` - Text chunk format
- `contracts/rag_build/EmbeddingJob.schema.json` - Embedding job configuration
- `contracts/rag_build/IndexConfig.schema.json` - Search index configuration

**Validation:**
```bash
python scripts/validate.py
python scripts/validate_cross_contracts.py
python scripts/validate_dependencies.py
pytest -q
```

**Note:** RAG build has no cross-dependencies yet; validation scripts exit cleanly.

## 🔒 Contract Hardening

The contract system includes pre-commit hooks and CI validation to ensure schema hygiene and consistency.

### Pre-commit
```bash
pip install pre-commit
pre-commit install
# runs automatically on commit for changed contract files
```

### CI
PRs touching `contracts/**` automatically run validators + tests via GitHub Actions.

### Local Validation Commands
```bash
python scripts/validate.py
python scripts/validate_cross_contracts.py
python scripts/validate_dependencies.py
pytest -q
```

## 🔍 RAG Pipeline

Build and serve RAG indices locally with full schema validation.

### Quick Start
```bash
# Build index from vectors and metadata
python -m rag_pipeline.cli index \
  --config rag_pipeline/configs/index_latency.json \
  --vectors artifacts/latency/vectors.npy \
  --metadata artifacts/latency/metadata.jsonl \
  --outdir artifacts/index/latency \
  --trace-id dev-idx-1

# Query the RAG service
python -m rag_pipeline.cli query \
  --mode latency \
  --index-dir artifacts/index/latency \
  --query "when urgency rises what protocol should I use?" \
  --top-k 3 \
  --trace-id dev-q-1
```

### Features
- **Schema Validation**: Full validation against build-time and serve-time schemas
- **Offline Operation**: No network calls, deterministic results
- **Multiple Metrics**: Cosine similarity, dot product, L2 distance
- **Filtering**: Support for doc_type and tag filters
- **Test Coverage**: Comprehensive test suite with fixtures

See `rag_pipeline/README.md` for detailed documentation.
