# RAG v0 (OpenAI Embeddings + FAISS)

A minimal, configurable RAG pipeline:
- Ingests protocols from `/Users/Nigel/Desktop/lichen-workspace/protocols`
- Chunks → Embeds (OpenAI text-embedding-3-small by default) → FAISS Index
- Searches with adjustable `k`
- Eval framework with console + JSON + Markdown "weekly scorecard"
- Drift audit vs Foundation Stones (`foundation_stones_path`)

**One-time setup**
```bash
pip install openai faiss-cpu pyyaml tqdm pandas pytest pytest-asyncio
export OPENAI_API_KEY=...   # required for embedding
```

**Build & search**
```bash
make build-corpus
make chunk
make embed
make search Q="i'm exhausted but need to push through"
```

**Eval & drift**
```bash
make eval
make drift
```

Tweak parameters in `rag_v0/config.yaml`.
