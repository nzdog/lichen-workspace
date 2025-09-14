# Protocol Router Implementation

## Overview

The Protocol Router is a semantic routing system that maps user queries to the most relevant 1-3 protocols, enabling scoped retrieval for improved precision and grounding. The router uses a weighted blend of semantic similarity, stones alignment, and keyword matching to make routing decisions.

## Architecture

```
Query → Parse → Route → Filter FAISS → Retrieve → Rerank
  ↓       ↓       ↓         ↓           ↓         ↓
Text   Signals  Top-3   Protocol    Scoped    Final
Input  Extract  Prots   Filtering   Results   Results
```

## Components

### 1. Core Router (`rag/router.py`)

**Key Classes:**
- `ProtocolRouter`: Main router class with configuration and routing logic
- `ParsedQuery`: Structured representation of parsed query with signals
- `RouteDecision`: Router output with candidates and confidence
- `ProtocolEntry`: Protocol catalog entry with metadata and embeddings

**Key Methods:**
- `build_protocol_catalog()`: Builds protocol catalog with centroid embeddings
- `parse_query()`: Extracts stones signals, keywords, and intents from query
- `route_query()`: Routes query to top protocol candidates using weighted scoring

**Scoring Algorithm:**
```python
score = (embed_sim * 0.6) + (stones_overlap * 0.2) + (keyword_match * 0.2)
```

**Confidence Thresholds:**
- `≥ 0.45`: Route to single protocol
- `≥ 0.30`: Route to top 2 protocols  
- `≥ 0.22`: Route to top 3 protocols
- `< 0.22`: Route to all protocols (global search)

### 2. RAG Integration (`hallway/adapters/rag_adapter.py`)

**Enhanced Methods:**
- `retrieve(query, lane, use_router=True)`: Added router integration
- Protocol filtering with fallback to global search
- Router decision logging in results
- Top-up mechanism when filtering reduces results

**Router Flow:**
1. Parse query and route to protocols
2. Filter FAISS candidates by `protocol_id`
3. If insufficient results, top-up with global search
4. Apply lane-specific reranking (MMR or cross-encoder)
5. Return results with router metadata

### 3. Configuration Updates

**`config/rag.yaml`:**
```yaml
router:
  enabled: true
  k: 3
  min_conf_single: 0.45
  min_conf_double: 0.30
  min_conf_triple: 0.22
  weights:
    embed: 0.6
    stones: 0.2
    keywords: 0.2
  cache_path: .vector/catalog_{model}.pkl

fast:
  top_k: 20  # Increased for router filtering

accurate:
  top_k_retrieve: 50  # Increased for router filtering
  top_k_rerank: 10
```

**`config/models.yaml`:**
```yaml
fast:
  embed_model: all-MiniLM-L6-v2

accurate:
  embed_model: all-MiniLM-L6-v2  # Same model for router compatibility
  reranker_model: cross-encoder/ms-marco-electra-base
```

### 4. CLI Commands (`rag/cli.py`)

**Available Commands:**
```bash
# Build protocol catalog
python3 -m rag.cli build-catalog --model sentence-transformers/all-MiniLM-L6-v2

# Test single query routing
python3 -m rag.cli test-route --query "leadership feels heavy" --k 3

# Batch test multiple queries
python3 -m rag.cli batch-test --input queries.json --output results.json
```

### 5. Evaluation Integration (`eval/run_eval.py`)

**New CLI Arguments:**
```bash
# Run with router (default)
python3 -m eval.run --router

# Run without router
python3 -m eval.run --no-router

# Debug retrieval with router info
python3 -m eval.run --router --debug-retrieval
```

**Enhanced Output:**
- Router decisions in evaluation records
- Router confidence and route type per query
- CSV export for router analysis (`eval/generate_router_analysis.py`)

### 6. Testing (`tests/test_router_and_retrieval.py`)

**Test Coverage:**
- Router core functionality (parsing, routing, scoring)
- RAG adapter integration with router
- End-to-end routing scenarios
- Confidence threshold behavior
- Fallback mechanisms

**Test Scenarios:**
- Leadership queries → "leadership_carrying" protocol
- Pace queries → "pace_gate" protocol  
- Mirror queries → "mirror" protocol
- Low confidence → global search fallback

## Usage Examples

### 1. Build Protocol Catalog

```bash
# From lichen-workspace root directory
# Build catalog with default model
python3 -m rag.cli build-catalog

# Build with specific model
python3 -m rag.cli build-catalog --model sentence-transformers/all-MiniLM-L6-v2
```

### 2. Test Routing

```bash
# From lichen-workspace root directory
# Test single query
python3 -m rag.cli test-route --query "leadership feels heavy / hidden load"

# Test with output file
python3 -m rag.cli test-route --query "I'm rushing and losing trust" --output result.json

# Test mirror query
python3 -m rag.cli test-route --query "reflect back my words clearly"
```

### 3. Run Evaluations

```bash
# Fast lane with router
python3 -m eval.run --lane fast --router --debug-retrieval

# Accurate lane with router  
python3 -m eval.run --lane accurate --router --debug-retrieval

# A/B comparison
python3 -m eval.run --lane fast --no-router
python3 -m eval.run --lane fast --router
```

### 4. Analyze Router Performance

```bash
# Generate router decisions CSV
python3 eval/generate_router_analysis.py --records eval/out/records_fast.jsonl --analyze

# View router decisions
python3 eval/generate_router_analysis.py --records eval/out/records_accurate.jsonl --output router_analysis.csv
```

## Expected Performance Improvements

Based on the implementation design:

### Precision/MRR Improvements
- **Scoped retrieval** reduces noise from irrelevant protocols
- **Reranker effectiveness** increases with higher-quality candidates
- **Expected improvement**: 15-25% in MRR@10

### Recall@20 Maintenance
- **Top-up mechanism** ensures coverage when filtering is too restrictive
- **Multi-protocol routing** (up to 3 protocols) maintains breadth
- **Expected**: Maintain current recall levels or slight improvement

### Grounding Score Improvements
- **Thematic alignment** between query and retrieved chunks
- **Stones-based routing** ensures protocol relevance
- **Expected improvement**: ≥0.5 average grounding score increase

### Latency Impact
- **Fast lane**: ≤20% latency increase (router overhead)
- **Accurate lane**: Minimal impact (reranker dominates)
- **Caching**: Protocol catalog cached for performance

## Implementation Notes

### Stones Mapping
The router includes a synonyms mapping for common query terms:
```python
stones_synonyms = {
    "stewardship": ["burnout", "burden", "weight", "heavy", "carrying", "load"],
    "speed": ["rushing", "haste", "urgency", "pace", "rhythm", "fast"],
    "trust": ["trust", "confidence", "reliability", "dependable"],
    # ... more mappings
}
```

### Key Phrase Extraction
Protocol key phrases are extracted from:
- Theme names
- Guiding questions (first 3-5 words)
- Outcomes (short phrases from expected/excellent)
- Completion prompts (first 2-4 words)

### Embedding Strategy
- **Centroid embeddings** computed by averaging:
  - Protocol title
  - Theme names (from stones)
  - Key phrases
  - Tags and fields
- **Normalized** for cosine similarity
- **Cached** to `.vector/catalog_{model}.pkl`

### Fallback Mechanisms
1. **Router failure** → Global search
2. **Low confidence** → Global search  
3. **Insufficient filtered results** → Top-up with global search
4. **Missing dependencies** → Keyword-only routing

## File Structure

```
lichen-workspace/                    # Root directory
├── rag/                            # Protocol Router (moved to root)
│   ├── __init__.py
│   ├── router.py                   # Core router implementation
│   └── cli.py                     # CLI commands
├── protocols/                      # Protocol data (moved to root)
│   ├── resourcing_mini_walk.json
│   ├── leadership_carrying.json
│   └── ... (all protocol files)
├── config/
│   ├── rag.yaml                   # Updated with router config
│   └── models.yaml                # Updated for router compatibility
├── lichen-protocol-mvp/
│   ├── hallway/adapters/
│   │   └── rag_adapter.py         # Enhanced with router integration
│   └── config/
│       └── rag.yaml               # Original config (backup)
├── eval/
│   ├── run_eval.py                # Enhanced with router support
│   ├── adapter.py                 # Updated retrieve() method
│   └── generate_router_analysis.py
├── tests/
│   └── test_router_and_retrieval.py
└── test_router_smoke.py           # Smoke test for verification
```

## Verification

Run the smoke test to verify implementation:

```bash
# From lichen-workspace root directory
python3 test_router_smoke.py
```

Expected output:
```
🎉 All tests passed! Router implementation is ready.
```

Test the CLI commands:

```bash
# Test routing scenarios
python3 -m rag.cli test-route --query "leadership feels heavy / hidden load"
python3 -m rag.cli test-route --query "I'm rushing and losing trust / pace off"
python3 -m rag.cli test-route --query "reflect back my words clearly"
```

## Next Steps

1. **Build protocol catalog**: `python3 -m rag.cli build-catalog`
2. **Run baseline evaluation**: `python3 -m eval.run --no-router`
3. **Run router evaluation**: `python3 -m eval.run --router`
4. **Compare results**: Analyze metrics improvements
5. **Tune thresholds**: Adjust confidence thresholds based on results
6. **Monitor performance**: Use router analysis tools for ongoing optimization

The Protocol Router implementation is complete and ready for evaluation and deployment.
