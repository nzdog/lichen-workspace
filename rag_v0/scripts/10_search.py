#!/usr/bin/env python3
import os, json, yaml, argparse, numpy as np, faiss
from openai import OpenAI

def l2norm(a):
    n = np.linalg.norm(a, axis=1, keepdims=True) + 1e-12
    return a / n

ap = argparse.ArgumentParser()
ap.add_argument("--query", dest="query", required=False, default=None)
ap.add_argument("--k", type=int, default=None)
args = ap.parse_args()

cfg = yaml.safe_load(open("rag_v0/config.yaml","r",encoding="utf-8"))
k = args.k or cfg["retrieval"]["k"]
index = faiss.read_index(cfg["index"]["path"])
meta = json.load(open(cfg["index"]["meta_path"],"r",encoding="utf-8"))
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def embed_q(q):
    e = client.embeddings.create(model=cfg["embedding"]["model"], input=[q]).data[0].embedding
    return l2norm(np.array([e], dtype="float32"))

def search(q):
    Q = embed_q(q)
    D, I = index.search(Q, k)
    out = []
    for rank,(idx,score) in enumerate(zip(I[0],D[0]),1):
        m = meta[str(idx)]
        out.append({
            "rank": rank,
            "score": float(score),
            "id": m["id"],
            "protocol_id": m["protocol_id"],
            "title": m["title"],
            "snippet": m["text"][:220].replace("\n"," ")
        })
    return out

if __name__ == "__main__":
    if not args.query:
        print(json.dumps({"error":"--query required or use make search Q='…'"}, indent=2))
    else:
        print(json.dumps(search(args.query), ensure_ascii=False, indent=2))
