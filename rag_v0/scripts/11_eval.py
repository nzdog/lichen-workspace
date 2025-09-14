#!/usr/bin/env python3
import time, json, yaml, subprocess, numpy as np, pathlib, datetime as dt

def p95(xs): return float(np.percentile(xs,95)) if xs else 0.0

def ndcg_at_k(rels, k=10):
    def dcg(xs): return sum((r/np.log2(i+2) for i,r in enumerate(xs[:k])))
    ideal = sorted(rels, reverse=True); idcg = dcg(ideal) or 1e-9
    return dcg(rels)/idcg

def main():
    cfg = yaml.safe_load(open("rag_v0/config.yaml","r",encoding="utf-8"))
    evalset = [json.loads(l) for l in open(cfg["eval"]["dataset"],"r",encoding="utf-8")]
    k = cfg["eval"]["topk_for_metrics"]
    lat_tgt = cfg["eval"]["latency_p95_target_ms"]
    
    latencies=[]; covered=0; P5=[]; R20=[]; MRR10=[]; NDCG10=[]
    for row in evalset:
        t0=time.time()
        res=json.loads(subprocess.check_output(["python3","rag_v0/scripts/10_search.py","--query",row["query"],"--k",str(k)]).decode("utf-8"))
        latencies.append((time.time()-t0)*1000)
        if not res: continue
        covered+=1
        
        positives=set(row.get("positives", []))
        rel=[1 if (r["id"] in positives or r["protocol_id"] in positives) else 0 for r in res]
        P5.append(sum(rel[:5])/5.0)
        denom=min(20,max(1,len(positives))); R20.append(sum(rel[:20])/denom)
        
        mrr=0.0
        for i,r in enumerate(rel[:10],1):
            if r: mrr=1.0/i; break
        MRR10.append(mrr)
        NDCG10.append(ndcg_at_k(rel,10))
    
    out={
        "precision_at_5": float(np.mean(P5)) if P5 else 0.0,
        "recall_at_20": float(np.mean(R20)) if R20 else 0.0,
        "mrr_at_10": float(np.mean(MRR10)) if MRR10 else 0.0,
        "ndcg_at_10": float(np.mean(NDCG10)) if NDCG10 else 0.0,
        "coverage": covered/len(evalset) if evalset else 0.0,
        "latency_ms_p95": p95(latencies),
        "num_queries": len(evalset),
        "latency_budget_ms": lat_tgt
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    
    # write weekly scorecard
    out_dir=pathlib.Path(cfg["eval"]["out_dir"]); out_dir.mkdir(parents=True, exist_ok=True)
    ts=dt.datetime.now().strftime("%Y-%m-%d")
    json.dump(out, open(out_dir/f"scorecard_{ts}.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(out_dir/f"scorecard_{ts}.md","w",encoding="utf-8") as md:
        md.write(f"# Weekly RAG Scorecard ({ts})\n\n")
        for k,v in out.items(): md.write(f"- {k}: {v}\n")

if __name__ == "__main__":
    main()
