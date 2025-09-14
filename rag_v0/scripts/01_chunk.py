#!/usr/bin/env python3
import re, json, yaml, pathlib

SENT = re.compile(r"(?<=[.!?])\s+")
def sentences(s): return [x.strip() for x in SENT.split(s or "") if x.strip()]

def main():
    cfg = yaml.safe_load(open("rag_v0/config.yaml","r",encoding="utf-8"))
    window, overlap = cfg["chunking"]["window"], cfg["chunking"]["overlap"]
    src = pathlib.Path(cfg["corpus"]["protocols_path"])
    dst = pathlib.Path(cfg["corpus"]["chunks_path"])
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    with open(src,"r",encoding="utf-8") as f, open(dst,"w",encoding="utf-8") as out:
        for line in f:
            row = json.loads(line)
            sents = sentences(row["text"])
            buf, i = "", 0
            
            def emit(txt):
                nonlocal i
                if not txt.strip(): return
                cid = f"{row['protocol_id']}#{i:04d}"
                out.write(json.dumps({
                    "id": cid,
                    "protocol_id": row["protocol_id"],
                    "title": row["title"],
                    "text": txt
                }, ensure_ascii=False) + "\n")
                i += 1
            
            for s in sents:
                nxt = (buf + " " + s).strip()
                if len(nxt) <= window:
                    buf = nxt
                else:
                    emit(buf)
                    buf = (buf[-overlap:] if overlap>0 else "") + " " + s
            emit(buf)

if __name__ == "__main__":
    main()
