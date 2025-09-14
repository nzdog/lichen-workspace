#!/usr/bin/env python3
import os, sys, json, pathlib, glob, re, yaml
from typing import List

def read_json(p: str) -> str:
    try:
        j = json.load(open(p, "r", encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"bad json {p}: {e}")
    # try to compose a decent text field
    fields = []
    for k in ("Overall Purpose","Why This Matters","Description","Text","Body"):
        v = j.get(k)
        if isinstance(v, str): fields.append(v)
    # themes/questions if present
    for t in j.get("Themes", []) or []:
        if isinstance(t, dict):
            for k in ("Purpose of This Theme","Why This Matters"):
                v = t.get(k)
                if isinstance(v, str): fields.append(v)
            for q in t.get("Guiding Questions", []) or []:
                if isinstance(q, str): fields.append(f"Q: {q}")
    if not fields:
        # fallback: serialize everything
        fields.append(json.dumps(j, ensure_ascii=False))
    title = j.get("Title") or pathlib.Path(p).stem
    pid = j.get("Protocol ID") or pathlib.Path(p).stem
    return title, pid, "\n".join(fields).strip()

def read_md(p: str) -> str:
    txt = open(p, "r", encoding="utf-8").read()
    title = pathlib.Path(p).stem
    pid = title
    # strip leading headers to form text body
    body = re.sub(r"^#.*\n", "", txt, flags=re.M).strip()
    return title, pid, body

def main():
    cfg = yaml.safe_load(open("rag_v0/config.yaml","r",encoding="utf-8"))
    indir = cfg["corpus"]["input_dir"]
    pats = cfg["corpus"]["patterns"]
    outp = pathlib.Path(cfg["corpus"]["protocols_path"])
    outp.parent.mkdir(parents=True, exist_ok=True)
    
    files: List[str] = []
    for pat in pats:
        # Ensure pattern has * prefix for glob
        pattern = f"*{pat}" if not pat.startswith("*") else pat
        files.extend(glob.glob(os.path.join(indir, "**", pattern), recursive=True))
    
    with open(outp, "w", encoding="utf-8") as w:
        for p in sorted(set(files)):
            try:
                if p.endswith(".json"):
                    title, pid, text = read_json(p)
                else:
                    title, pid, text = read_md(p)
                row = {
                    "protocol_id": pid,
                    "title": title,
                    "text": text,
                    "path": p
                }
                w.write(json.dumps(row, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"[skip] {p}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
