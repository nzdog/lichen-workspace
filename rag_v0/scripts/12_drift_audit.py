#!/usr/bin/env python3
import json, yaml, numpy as np, pathlib, re, os
from openai import OpenAI

def l2norm(a):
    n = np.linalg.norm(a, axis=-1, keepdims=True) + 1e-12
    return a / n

def embed(texts, model):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    out=[]
    for i in range(0,len(texts),128):
        batch=texts[i:i+128]
        resp=client.embeddings.create(model=model, input=batch)
        out.extend([d.embedding for d in resp.data])
    return l2norm(np.array(out, dtype="float32"))

def main():
    cfg=yaml.safe_load(open("rag_v0/config.yaml","r",encoding="utf-8"))
    stones_path=cfg["drift"]["foundation_stones_path"]
    stones_text=open(stones_path,"r",encoding="utf-8").read()
    stones_terms=[t.strip() for t in re.split(r"[\n,;/]", stones_text) if t.strip()]
    
    # take the top-k from a canonical query set (evalset) and measure overlap
    eval_rows=[json.loads(l) for l in open(cfg["eval"]["dataset"],"r",encoding="utf-8")]
    # build one big sample corpus of top contexts
    from subprocess import check_output
    contexts=[]
    for r in eval_rows:
        js=json.loads(check_output(["python3","rag_v0/scripts/10_search.py","--query",r["query"],"--k","20"]).decode("utf-8"))
        contexts.extend([x["snippet"] for x in js[:10]])
    contexts_text="\n".join(contexts)
    
    # keyword coverage
    hits=sum(1 for t in stones_terms if re.search(r"\b"+re.escape(t)+r"\b", contexts_text, flags=re.I))
    coverage = (hits/max(1,len(stones_terms)))
    
    # semantic similarity between stones and contexts (mean embeddings)
    stones_vec=embed([stones_text], cfg["embedding"]["model"])[0]
    ctx_vec=embed([contexts_text], cfg["embedding"]["model"])[0]
    sim=float(np.dot(stones_vec, ctx_vec.T))
    
    out={
        "stones_terms_total": len(stones_terms),
        "stones_terms_hit": hits,
        "keyword_coverage": coverage,
        "semantic_similarity": sim,
        "min_keyword_coverage": cfg["drift"]["min_keyword_coverage"],
        "min_semantic_sim": cfg["drift"]["min_semantic_sim"]
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    
    # write to eval/out as well
    out_dir=pathlib.Path(cfg["eval"]["out_dir"]); out_dir.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(out_dir/"drift_latest.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
