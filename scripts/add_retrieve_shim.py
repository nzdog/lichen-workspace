import sys, pathlib

p = pathlib.Path(sys.argv[1]).resolve()
text = p.read_text(encoding="utf-8")

if "def retrieve(" in text and "def build_retriever(" in text:
    print("Shim already present:", p)
    sys.exit(0)

shim = r'''

# -----------------------
# Convenience construction & shim API
# -----------------------
from typing import Optional, Dict, Any, List

def _infer_stats_path(index_path: Optional[str]) -> Optional[str]:
    if not index_path:
        return None
    p = str(index_path)
    if p.endswith(".faiss"):
        return p.replace(".faiss", ".stats.json")
    return p + ".stats.json"

def build_retriever(config: Optional[Dict[str, Any]] = None) -> "ProtocolFirstHybridRetriever":
    cfg = dict(config or {})

    fast_index_path = os.getenv("FAST_INDEX_PATH", cfg.get("fast_index_path"))
    fast_stats_path = os.getenv("FAST_STATS_PATH", cfg.get("fast_stats_path") or _infer_stats_path(fast_index_path))
    fast_meta_path  = os.getenv("FAST_META_PATH",  cfg.get("fast_meta_path"))

    accurate_index_path = os.getenv("ACCURATE_INDEX_PATH", cfg.get("accurate_index_path"))
    accurate_stats_path = os.getenv("ACCURATE_STATS_PATH", cfg.get("accurate_stats_path") or _infer_stats_path(accurate_index_path))
    accurate_meta_path  = os.getenv("ACCURATE_META_PATH",  cfg.get("accurate_meta_path"))

    protocol_catalog_path = os.getenv("PROTOCOL_CATALOG_PATH", cfg.get("protocol_catalog_path"))

    embed_model_fast     = os.getenv("EMBED_MODEL_FAST",     cfg.get("embed_model_fast", "sentence-transformers/all-MiniLM-L6-v2"))
    embed_model_accurate = os.getenv("EMBED_MODEL_ACCURATE", cfg.get("embed_model_accurate", "sentence-transformers/all-MiniLM-L6-v2"))
    cross_encoder_model  = os.getenv("CROSS_ENCODER_MODEL",  cfg.get("cross_encoder_model", ""))

    merged = {
        "fast_index_path": fast_index_path, "fast_stats_path": fast_stats_path, "fast_meta_path": fast_meta_path,
        "accurate_index_path": accurate_index_path, "accurate_stats_path": accurate_stats_path, "accurate_meta_path": accurate_meta_path,
        "protocol_catalog_path": protocol_catalog_path,
        "embed_model_fast": embed_model_fast, "embed_model_accurate": embed_model_accurate,
        "cross_encoder_model": cross_encoder_model,
    }
    return ProtocolFirstHybridRetriever(merged)

def retrieve(query_text: str, top_k: int = 8, lane: str = "fast"):
    r = build_retriever()
    lane = (lane or "fast").lower()
    if lane.startswith("acc"):
        return r.retrieve_accurate(query_text, top_k=top_k)
    return r.retrieve_fast(query_text, top_k=top_k)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", choices=["fast","accurate"], default="fast")
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("query", nargs="*", help="Query text")
    args = ap.parse_args()
    q = " ".join(args.query) or "how do I realign our sales stages to field reality?"
    res = retrieve(q, top_k=args.top_k, lane=args.lane)
    print(f"{len(res)} results ({args.lane})")
    for r in res[:args.top_k]:
        mid = (r.get("metadata") or {}).get("protocol_id", "?")
        print("-", mid, "→", (r.get("text","")[:80] + "..."))
'''
p.write_text(text.rstrip() + "\n" + shim, encoding="utf-8")
print("Shim appended to:", p)
