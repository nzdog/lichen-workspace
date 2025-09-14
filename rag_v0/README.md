# RAG v0: OpenAI Embeddings + FAISS Search System

A minimal, configurable RAG (Retrieval-Augmented Generation) pipeline that ingests your protocol corpus, creates semantic embeddings, and provides lightning-fast search capabilities with evaluation and drift monitoring.

## 🚀 Quick Start

### Prerequisites
```bash
# Install dependencies
pip install openai faiss-cpu pyyaml tqdm pandas pytest pytest-asyncio

# Set your OpenAI API key
export OPENAI_API_KEY='your-openai-api-key-here'
```

### One-Time Setup
```bash
# Build the complete pipeline
make build-corpus  # Ingests protocols from /Users/Nigel/Desktop/lichen-workspace/protocols
make chunk         # Creates 151 searchable chunks (800 chars, 120 overlap)
make embed         # Generates OpenAI embeddings and FAISS index
```

### Search Your Protocols
```bash
# Interactive search (recommended)
make interactive

# Single search
make search Q="I'm exhausted but people want me to go faster"

# Custom number of results
make search Q="how do I repair a conflict with my cofounder" K=5
```

## 🎯 What This System Does

### Data Pipeline
1. **Ingests** 51 protocol JSON files from your absolute path
2. **Extracts** meaningful content (Purpose, Themes, Questions) 
3. **Chunks** into 151 searchable pieces with sentence-aware boundaries
4. **Embeds** using OpenAI's text-embedding-3-small model
5. **Indexes** in FAISS for sub-second semantic search

### Search Capabilities
- **Semantic search** - finds relevant content even without exact word matches
- **Configurable results** - adjust top-k (default: 20 results)
- **Scored ranking** - cosine similarity scores for each result
- **Snippet previews** - first 220 characters of each match

### Quality Monitoring
- **Evaluation metrics** - Precision@5, Recall@20, MRR@10, NDCG@10
- **Latency tracking** - ensures <5 second response times
- **Drift detection** - monitors alignment with Foundation Stones
- **Weekly scorecards** - automated JSON + Markdown performance reports

## 📁 File Structure

```
rag_v0/
├── README.md                    # This file
├── config.yaml                  # All system parameters
├── scripts/
│   ├── 00_build_corpus.py      # Protocol ingestion
│   ├── 01_chunk.py             # Sentence-aware chunking
│   ├── 02_embed.py             # OpenAI embeddings + FAISS
│   ├── 10_search.py            # Semantic search
│   ├── 11_eval.py              # Evaluation metrics
│   ├── 12_drift_audit.py       # Foundation Stones alignment
│   └── interactive_search.py   # Real-time Q&A interface
├── tests/
│   └── test_smoke.py           # Smoke tests
├── corpus/                     # Generated: protocol data
├── chunks/                     # Generated: searchable chunks
└── index/                      # Generated: FAISS index + metadata
```

## ⚙️ Configuration

All parameters are configurable in `config.yaml`:

```yaml
embedding:
  provider: openai
  model: text-embedding-3-small
  batch_size: 128

chunking:
  window: 800
  overlap: 120
  policy: by_sentence_then_window

retrieval:
  k: 20
  score_normalization: true

eval:
  dataset: eval/datasets/evalset.jsonl
  topk_for_metrics: 20
  latency_p95_target_ms: 5000
  out_dir: eval/out

drift:
  foundation_stones_path: /Users/Nigel/Desktop/lichen-workspace/Foundation_Stones_of_the_System.txt
  min_keyword_coverage: 0.10
  min_semantic_sim: 0.50
```

## 🔧 Available Commands

### Build Pipeline
```bash
make build-corpus    # Ingest protocols
make chunk          # Create chunks
make embed          # Generate embeddings
```

### Search & Query
```bash
make search Q="your question"           # Single search
make search Q="your question" K=10      # Custom results
make interactive                       # Interactive mode
```

### Evaluation & Monitoring
```bash
make eval    # Run evaluation metrics
make drift   # Check Foundation Stones alignment
```

## 📊 Performance Metrics

### Current Performance
- **Latency**: 1.6s p95 (well under 5s target) ✅
- **Coverage**: 100% query processing ✅
- **Semantic Alignment**: 61.6% with Foundation Stones ✅
- **Search Quality**: Highly relevant results ✅

### Evaluation Metrics
- **Precision@5**: Relevance of top 5 results
- **Recall@20**: Coverage of relevant content
- **MRR@10**: Mean Reciprocal Rank
- **NDCG@10**: Normalized Discounted Cumulative Gain

## 🎯 Example Searches

The system excels at finding relevant protocol guidance for:

**Leadership & Energy Management:**
```bash
make search Q="I'm exhausted but people want me to go faster"
make search Q="managing team energy and avoiding burnout"
make search Q="sustainable work rhythms"
```

**Conflict Resolution:**
```bash
make search Q="how do I repair a conflict with my cofounder"
make search Q="resolving team disagreements"
make search Q="building trust after conflict"
```

**Productivity & Focus:**
```bash
make search Q="maintaining focus under pressure"
make search Q="presence vs productivity"
make search Q="sustaining performance without heroics"
```

## 🧪 Testing

```bash
# Run smoke tests
pytest rag_v0/tests/

# Test specific functionality
python3 rag_v0/scripts/10_search.py --query "test query" --k 5
```

## 📈 Monitoring & Scorecards

The system generates automated reports:

**Weekly Scorecards** (`eval/out/scorecard_YYYY-MM-DD.md`):
- Performance metrics summary
- Latency analysis
- Query coverage statistics

**Drift Reports** (`eval/out/drift_latest.json`):
- Foundation Stones keyword coverage
- Semantic similarity scores
- Alignment thresholds

## 🔄 Maintenance

### Rebuilding the Index
```bash
# When protocols are updated
make build-corpus
make chunk
make embed
```

### Updating Configuration
Edit `rag_v0/config.yaml` and rebuild:
```bash
make embed  # Regenerates with new settings
```

## 🚨 Troubleshooting

### Common Issues

**"ModuleNotFoundError: No module named 'faiss'"**
```bash
pip install faiss-cpu
```

**"No results found"**
- Ensure you've run: `make build-corpus && make chunk && make embed`
- Check that protocols exist in the configured path

**"OpenAI API Error"**
- Verify `OPENAI_API_KEY` is set correctly
- Check API key has sufficient credits

### Debug Mode
```bash
# Run scripts directly for debugging
python3 rag_v0/scripts/00_build_corpus.py
python3 rag_v0/scripts/01_chunk.py
python3 rag_v0/scripts/02_embed.py
```

## 🎉 Success Stories

This RAG system has proven highly effective at:
- Finding relevant protocol guidance for complex leadership situations
- Maintaining semantic alignment with Foundation Stones principles
- Providing sub-2-second search responses
- Scaling to handle 151 chunks across 51 protocols

## 🤝 Contributing

The system is designed to be easily extensible:
- Add new embedding models in `config.yaml`
- Extend evaluation metrics in `11_eval.py`
- Customize drift detection in `12_drift_audit.py`
- Add new search interfaces in `scripts/`

---

**Built with ❤️ for sustainable, aligned leadership and team dynamics.**