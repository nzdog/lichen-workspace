---
# RAG Legacy (Quarantine)

All pre-v0 RAG code, tests, tools, indices, and configs have been moved here to keep the main workspace clean while we rebuild a minimal `rag_v0/`. Nothing in this directory is considered active. Keep for reference and diffing only.

- Active RAG: `rag_v0/`
- Quarantined tests: `rag_legacy/tests/`
- Quarantined configs: `rag_legacy/**/config/`
- Quarantined schemas: `rag_legacy/**/contracts/rag/`
- Quarantined tools: `rag_legacy/**/tools/`
- 2025-09-14: Moved remaining legacy RAG-bound code (`eval/adapter.py`, `run_eval.py`, legacy FAISS scripts, and hybrid test) to quarantine. Active work should use `rag_v0/`.
---
