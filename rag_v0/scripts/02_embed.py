#!/usr/bin/env python3
import os, json, yaml, pathlib, numpy as np
from tqdm import tqdm
import faiss

def openai_embed(texts, model, batch_size=128):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    out = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        resp = client.embeddings.create(model=model, input=batch)
        out.extend([d.embedding for d in resp.data])
    return np.array(out, dtype="float32")

def l2norm(a):
    n = np.linalg.norm(a, axis=1, keepdims=True) + 1e-12
    return a / n

def main():
    cfg = yaml.safe_load(open("rag_v0/config.yaml","r",encoding="utf-8"))
    chunks_path = pathlib.Path(cfg["corpus"]["chunks_path"])
    index_path = pathlib.Path(cfg["index"]["path"])
    meta_path = pathlib.Path(cfg["index"]["meta_path"])
    index_path.parent.mkdir(parents=True, exist_ok=True)
    
    texts, metas = [], []
    with open(chunks_path,"r",encoding="utf-8") as f:
        for line in f:
            j = json.loads(line)
            texts.append(j["text"])
            metas.append({k:j[k] for k in ("id","protocol_id","title","text")})
    
    if cfg["embedding"]["provider"] == "openai":
        embs = openai_embed(texts, cfg["embedding"]["model"], cfg["embedding"]["batch_size"])
    else:
        raise RuntimeError("Only provider=openai supported in v0 (switchable later).")
    
    embs = l2norm(embs).astype("float32")
    dim = embs.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embs)
    
    faiss.write_index(index, str(index_path))
    json.dump({i:m for i,m in enumerate(metas)}, open(meta_path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
