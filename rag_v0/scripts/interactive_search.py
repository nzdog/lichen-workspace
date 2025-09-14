#!/usr/bin/env python3
import os, json, yaml, argparse, numpy as np, faiss, sys
from openai import OpenAI

def l2norm(a):
    n = np.linalg.norm(a, axis=1, keepdims=True) + 1e-12
    return a / n

def load_index():
    cfg = yaml.safe_load(open("rag_v0/config.yaml","r",encoding="utf-8"))
    index = faiss.read_index(cfg["index"]["path"])
    meta = json.load(open(cfg["index"]["meta_path"],"r",encoding="utf-8"))
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return cfg, index, meta, client

def embed_q(q, cfg, client):
    e = client.embeddings.create(model=cfg["embedding"]["model"], input=[q]).data[0].embedding
    return l2norm(np.array([e], dtype="float32"))

def search(query, cfg, index, meta, client, k=20):
    Q = embed_q(query, cfg, client)
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

def format_results(results, max_results=10):
    print(f"\n🔍 Found {len(results)} results (showing top {min(max_results, len(results))}):")
    print("=" * 80)
    
    for i, r in enumerate(results[:max_results]):
        print(f"\n{i+1}. {r['title']} (Score: {r['score']:.3f})")
        print(f"   Protocol: {r['protocol_id']}")
        print(f"   {r['snippet']}...")
    
    if len(results) > max_results:
        print(f"\n... and {len(results) - max_results} more results")

def main():
    print("🚀 RAG v0 Interactive Search")
    print("=" * 50)
    print("Ask questions about your protocols!")
    print("Commands:")
    print("  - Type your question and press Enter")
    print("  - Type 'k=N' to change number of results (e.g., 'k=5')")
    print("  - Type 'quit' or 'exit' to stop")
    print("  - Type 'help' for more options")
    print()
    
    # Load index
    try:
        cfg, index, meta, client = load_index()
        print(f"✅ Loaded index with {len(meta)} chunks from {len(set(m['protocol_id'] for m in meta.values()))} protocols")
    except Exception as e:
        print(f"❌ Error loading index: {e}")
        print("Make sure you've run: make build-corpus && make chunk && make embed")
        return
    
    k = 10  # default results
    
    while True:
        try:
            query = input(f"\n🔍 Ask a question (k={k}): ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if query.lower() == 'help':
                print("\n📚 Help:")
                print("  - Ask any question about leadership, teams, conflict, energy, etc.")
                print("  - Type 'k=5' to show only 5 results")
                print("  - Type 'k=20' to show 20 results")
                print("  - Type 'quit' to exit")
                continue
            
            if query.startswith('k='):
                try:
                    k = int(query.split('=')[1])
                    print(f"✅ Set results to {k}")
                    continue
                except:
                    print("❌ Invalid format. Use 'k=5' or similar")
                    continue
            
            if not query:
                continue
            
            # Perform search
            print(f"\n🔍 Searching for: '{query}'")
            results = search(query, cfg, index, meta, client, k)
            
            if results:
                format_results(results, k)
            else:
                print("❌ No results found")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

if __name__ == "__main__":
    main()
