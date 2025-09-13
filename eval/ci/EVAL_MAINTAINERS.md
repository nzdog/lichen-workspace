# 🌙 Nightly RAG Evaluation — Maintainer Guide

This repo runs a **nightly evaluation** of the RAG backbone (fast + accurate lanes) via GitHub Actions.  
The job checks for regressions, uploads artifacts, and fails if metrics drift.

---

## 📅 Workflow
- File: `.github/workflows/eval-nightly.yml`
- Runs nightly at **02:30 UTC**
- Can also be run manually:
  ```bash
  gh workflow run eval-nightly.yml -f reason="manual run"
  gh run watch
  ```

---

## 📂 Artifacts
Each run uploads:
- `eval/out/records_fast.jsonl`
- `eval/out/records_accurate.jsonl`
- `eval/out/summary_fast.json`
- `eval/out/summary_accurate.json`

Artifacts are retained for **14 days**.

---

## 📊 Metrics & Regression Gate
Key metrics compared against the baseline:
- **coverage**
- **recall_at_20**
- **ndcg_at_10**

Tolerance: **0.01**
- Δ ≥ 0.01 → regression → job fails.
- On PR branches: failure + comment with metric deltas.
- On nightly schedule: failure + auto-created GitHub Issue.

---

## 📌 Baseline
Baseline summaries live in `.eval_baseline/`:
- `.eval_baseline/summary_fast.json`
- `.eval_baseline/summary_accurate.json`

To **update baseline** after intentional improvements:
```bash
python -m eval.run_eval --evalset eval/evalset.json --outdir eval/out

cp eval/out/summary_fast.json .eval_baseline/summary_fast.json
cp eval/out/summary_accurate.json .eval_baseline/summary_accurate.json

git add .eval_baseline
git commit -m "ci(eval): update baseline after improvements"
git push
```

---

## 🔧 Debugging Failures
1. Download run artifacts:
   ```bash
   gh run download <run-id> --dir eval_artifacts
   ```
2. Inspect `summary_*.json` for metric values.
3. Compare against `.eval_baseline` to see drift.
4. Decide:
   - **Bug/regression** → investigate pipeline.
   - **Expected change** → update baseline (see above).

---

## 🛡️ Redaction & Security
The workflow enforces redaction flags in `production` env:
- `PII_REDACTION=1`
- `LOG_REDACTION=1`
- `INTEGRITY_DEBUG=0`
- `ALLOW_PROMPT_LOGGING=0`
- `DISABLE_DEBUG_ENDPOINTS=1`

Logs/artifacts never include raw founder input or full protocol JSON.

---

## ✅ Quick Commands

Run eval locally (both lanes):
```bash
python -m eval.run_eval --evalset eval/evalset.json --outdir eval/out
```

Trigger nightly manually:
```bash
gh workflow run eval-nightly.yml -f reason="debug"
```

Watch run:
```bash
gh run watch
```

---

## 📈 Workflow at a Glance (Mermaid)

```mermaid
flowchart TD
    A[GitHub Actions Trigger] -->|02:30 UTC nightly<br/>or manual dispatch| B[Checkout Repo]
    B --> C[Set up Python 3.13 + deps]
    C --> D[Run eval.run_eval<br/>fast + accurate lanes]
    D --> E[Generate records + summaries]
    E --> F[Compare vs .eval_baseline<br/>(tolerance 0.01)]
    F -->|No regression| G[Upload artifacts + Update summary]
    F -->|Regression detected| H[Fail Job]
    H -->|On PR| I[Comment on PR]
    H -->|On nightly| J[Open GitHub Issue]
    G --> K[Artifacts retained 14 days]
```

---

## 📈 Workflow at a Glance (ASCII)

```
+---------------------------+
| GitHub Actions Trigger    |
|  - 02:30 UTC nightly      |
|  - manual dispatch        |
+-------------+-------------+
              |
              v
+-------------+-------------+
| Checkout Repo             |
+-------------+-------------+
              |
              v
+-------------+-------------+
| Setup Python 3.13 + deps  |
+-------------+-------------+
              |
              v
+-------------+-------------+
| Run eval.run_eval         |
|  - fast & accurate lanes  |
+-------------+-------------+
              |
              v
+-------------+-------------+
| Generate records &        |
| summaries                 |
+-------------+-------------+
              |
              v
+-------------+-------------+
| Compare vs .eval_baseline |
|  (tolerance 0.01)         |
+------+------+-------------+
       |            |
   No regression    | Regression
       |            v
       v     +------+-------------+
+-------------+     |   Fail Job  |
| Upload artifacts|  +------+-----+
| + update summary|         |
+-------------+---+   +-----+-----+
              |       |           |
              v       v           v
      (retained 14d) PR comment  Create Issue
```

---

💡 **Rule of thumb:** Baseline only moves forward on intentional, reviewed changes.  
If you see regressions, investigate first — don’t just overwrite the baseline.
