# RAG Evaluation CI Helpers

This directory contains helper scripts for the nightly RAG evaluation CI workflow.

## Scripts

### `check_regressions.py`

Compares current evaluation results against baseline to detect performance regressions.

**Usage:**
```bash
python eval/ci/check_regressions.py \
  --current-fast eval/out/summary_fast.json \
  --current-accurate eval/out/summary_accurate.json \
  --baseline-dir .eval_baseline \
  --tolerance 0.01 \
  --output-format json
```

**Key Metrics Checked:**
- Coverage
- Recall@20  
- nDCG@10

**Output:**
- Text format: Human-readable regression report
- JSON format: Machine-readable results for CI integration

### `generate_summary.py`

Generates formatted summary tables of evaluation results with optional baseline comparison.

**Usage:**
```bash
python eval/ci/generate_summary.py \
  --fast-summary eval/out/summary_fast.json \
  --accurate-summary eval/out/summary_accurate.json \
  --baseline-dir .eval_baseline \
  --output-format markdown
```

**Output:**
- Markdown format: GitHub-compatible tables with delta indicators
- Text format: Simple console output

## Regression Detection

Regressions are detected when key metrics change beyond the specified tolerance:

- **Tolerance**: 0.01 (1%) by default
- **Direction**: Higher is better for most metrics (coverage, recall, nDCG)
- **Latency**: Lower is better (increases are regressions)

## Baseline Management

The CI workflow automatically:
1. Updates baseline after successful runs (no regressions)
2. Compares against baseline for regression detection
3. Stores baseline in `.eval_baseline/` directory in the repository
