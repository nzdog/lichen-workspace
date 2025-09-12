# Staging Playbook

This document provides operational guidance for monitoring and debugging the Lichen Protocol in staging environments.

## RAG Log Filters (jq recipes)

The RAG observability system logs all operations to `lichen-protocol-mvp/logs/rag/*.jsonl`. Use these jq filters to analyze performance and debug issues.

### Lane Filtering

```bash
# Accurate lane only (last 200 lines)
tail -n 200 lichen-protocol-mvp/logs/rag/*.jsonl \
| jq -r 'select(.lane=="accurate")'

# Fast lane only
jq -r 'select(.lane=="fast")' lichen-protocol-mvp/logs/rag/*.jsonl
```

### Performance Analysis

```bash
# Slow turns: total >= 500ms
jq -r 'select(.stages.total_ms != null and .stages.total_ms >= 500)' lichen-protocol-mvp/logs/rag/*.jsonl

# Very slow turns: total >= 1000ms with timing breakdown
jq -r 'select(.stages.total_ms != null and .stages.total_ms >= 1000) 
       | "\(.ts) lane=\(.lane) total=\(.stages.total_ms)ms retrieve=\(.stages.retrieve_ms)ms rerank=\(.stages.rerank_ms)ms synth=\(.stages.synth_ms)ms"' \
       lichen-protocol-mvp/logs/rag/*.jsonl

# Top-K histogram (quick-and-dirty)
jq -r '.topk' lichen-protocol-mvp/logs/rag/*.jsonl | sort | uniq -c | sort -nr
```

### Quality Analysis

```bash
# Low grounding: < 0.25
jq -r 'select(.grounding_score != null and .grounding_score < 0.25)' lichen-protocol-mvp/logs/rag/*.jsonl

# Accurate + low grounding (and show a concise summary line)
jq -r 'select(.lane=="accurate" and (.grounding_score // 1) < 0.25)
       | "\(.ts) lane=\(.lane) g=\(.grounding_score) t=\(.stages.total_ms)ms req=\(.request_id)"' \
       lichen-protocol-mvp/logs/rag/*.jsonl

# No citations found
jq -r 'select(.citations | length == 0) | "\(.ts) lane=\(.lane) topk=\(.topk) g=\(.grounding_score // "null")"' \
       lichen-protocol-mvp/logs/rag/*.jsonl
```

### Fallback Analysis

```bash
# All fallback events
jq -r 'select(.flags.fallback != null)' lichen-protocol-mvp/logs/rag/*.jsonl

# RAG disabled events
jq -r 'select(.flags.rag_enabled == false)' lichen-protocol-mvp/logs/rag/*.jsonl

# Insufficient support events
jq -r 'select(.flags.fallback == "insufficient_support")' lichen-protocol-mvp/logs/rag/*.jsonl
```

### Stones Analysis

```bash
# Events with stones specified
jq -r 'select(.stones != null and (.stones | length > 0))' ligen-protocol-mvp/logs/rag/*.jsonl

# Stones alignment distribution
jq -r '.grounding_score' lichen-protocol-mvp/logs/rag/*.jsonl | grep -v null | sort -n
```

### Combined Filters

```bash
# Accurate lane + slow + low grounding (troubleshooting)
jq -r 'select(.lane=="accurate" and .stages.total_ms > 300 and (.grounding_score // 1) < 0.4)
       | "\(.ts) req=\(.request_id[0:8]) g=\(.grounding_score) t=\(.stages.total_ms)ms stones=\(.stones // [])"' \
       lichen-protocol-mvp/logs/rag/*.jsonl

# Recent events with citations
jq -r 'select((.citations | length > 0) and (.ts | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime) > (now - 3600))' \
       lichen-protocol-mvp/logs/rag/*.jsonl
```

## Tail Tool Usage

Use the custom tail tool for real-time monitoring with built-in filtering and p95 calculations:

```bash
# Follow logs with basic filtering
python tools/tail_rag_logs.py --follow --lane accurate --min-grounding 0.25 --slow-ms 500

# Monitor fast lane performance
python tools/tail_rag_logs.py --follow --lane fast --p95-window 100

# Review recent slow operations
python tools/tail_rag_logs.py --since 30 --slow-ms 200

# Debug low-quality responses
python tools/tail_rag_logs.py --since 60 --min-grounding 0.1 --lane accurate
```

### Tail Tool Options

- `--follow`: Follow log file like `tail -f`
- `--since N`: Show events from last N minutes (default: 60)
- `--lane {fast,accurate,any}`: Filter by RAG lane (default: any)
- `--min-grounding FLOAT`: Filter by minimum grounding score
- `--slow-ms INT`: Filter by minimum total latency in milliseconds
- `--p95-window N`: Rolling window size for p95 computation (default: 200)
- `--budget-check`: Check performance budgets (excludes warmup, shows pass/fail vs targets)

## Common Debugging Scenarios

### High Latency Investigation

```bash
# 1. Check for slow operations in last hour
python tools/tail_rag_logs.py --since 60 --slow-ms 1000

# 2. Break down by stage
jq -r 'select(.stages.total_ms > 500) 
       | "\(.stages.retrieve_ms)ms retrieve, \(.stages.rerank_ms)ms rerank, \(.stages.synth_ms)ms synth"' \
       lichen-protocol-mvp/logs/rag/*.jsonl | sort | uniq -c

# 3. Check if specific documents are slow
jq -r 'select(.stages.total_ms > 500) | .trace.used_doc_ids // []' \
       lichen-protocol-mvp/logs/rag/*.jsonl | jq -r '.[]' | sort | uniq -c
```

### Low Quality Investigation

```bash
# 1. Find low grounding scores
python tools/tail_rag_logs.py --since 120 --min-grounding 0.0 --lane accurate

# 2. Check stones alignment patterns
jq -r 'select(.grounding_score != null and .grounding_score < 0.3) 
       | "\(.grounding_score) stones=\(.stones // []) topk=\(.topk)"' \
       lichen-protocol-mvp/logs/rag/*.jsonl

# 3. Examine citation patterns
jq -r 'select((.citations | length) != (.topk // 0)) 
       | "topk=\(.topk) citations=\(.citations | length) lane=\(.lane)"' \
       lichen-protocol-mvp/logs/rag/*.jsonl | sort | uniq -c
```

### Lane Performance Comparison

```bash
# Compare p95 latencies by lane (requires multiple log analysis)
jq -r 'select(.lane=="fast") | .stages.total_ms' lichen-protocol-mvp/logs/rag/*.jsonl | sort -n
jq -r 'select(.lane=="accurate") | .stages.total_ms' lichen-protocol-mvp/logs/rag/*.jsonl | sort -n

# Count operations by lane
jq -r '.lane' lichen-protocol-mvp/logs/rag/*.jsonl | sort | uniq -c
```

## Alerting Thresholds

Recommended monitoring thresholds for staging:

- **Fast lane p95 latency**: > 200ms (warning), > 500ms (critical)
- **Accurate lane p95 latency**: > 800ms (warning), > 2000ms (critical)
- **Grounding score**: < 0.3 (warning), < 0.1 (critical)
- **Fallback rate**: > 5% (warning), > 15% (critical)
- **Citation coverage**: < 80% (warning when citations/topk < 0.8)

## Guardrails in Staging

The RAG system implements strict guardrails to prevent low-quality or unsupported responses:

### Grounding Threshold

- **Default threshold**: 0.25 (configurable in `config/rag.yaml`)
- **Environment override**: Set `MIN_GROUNDING=0.3` to override config
- **Behavior**: If grounding score < threshold → system refuses with safe fallback
- **Grounding calculation**: Based on citations presence, stones alignment, and hallucination rate

### Citations Requirement

- **Policy**: All claimful outputs must include at least one source reference
- **Structure**: Citations must have `{source_id, span}` format
- **Behavior**: Missing citations trigger fallback refusal
- **Fallback message**: "Cannot answer confidently: insufficient grounding."

### Monitoring Refusals

```bash
# Find all refusal events
jq 'select(.flags.fallback=="low_grounding" or .flags.fallback=="no_citations")' logs/rag/*.jsonl

# Count refusal types
jq -r '.flags.fallback' logs/rag/*.jsonl | grep -E "(low_grounding|no_citations)" | sort | uniq -c

# Recent refusals with details
jq -r 'select(.flags.refusal != null) 
       | "\(.ts) \(.flags.refusal) g=\(.grounding_score // "null") lane=\(.lane)"' \
       logs/rag/*.jsonl | tail -10

# Refusal rate by lane
jq -r 'select(.lane=="accurate") | .flags.fallback' logs/rag/*.jsonl | grep -c "low_grounding"
jq -r 'select(.lane=="fast") | .flags.fallback' logs/rag/*.jsonl | grep -c "low_grounding"
```

### Guardrail Configuration

```bash
# Check current threshold
jq '.limits.min_grounding' config/rag.yaml

# Temporarily adjust threshold for testing
MIN_GROUNDING=0.1 python tools/tail_rag_logs.py --follow --min-grounding 0.05

# Monitor impact of threshold changes
jq -r 'select(.grounding_score != null) 
       | "\(.grounding_score) \(.flags.fallback // "success")"' \
       logs/rag/*.jsonl | sort -n
```

### Quality Metrics

Track guardrail effectiveness:

- **Refusal rate**: Should be 5-15% in staging (indicates appropriate threshold)
- **False positive rate**: High-quality queries being refused (monitor manually)
- **Citation coverage**: Percentage of successful responses with citations
- **Grounding distribution**: Spread of grounding scores across lanes

```bash
# Citation coverage analysis
total=$(jq -s 'length' logs/rag/*.jsonl)
with_citations=$(jq -r 'select((.citations | length) > 0)' logs/rag/*.jsonl | wc -l)
echo "Citation coverage: $with_citations/$total"

# Grounding score distribution
jq -r '.grounding_score' logs/rag/*.jsonl | grep -v null | sort -n | uniq -c
```

## Performance Budget Monitoring

The RAG system implements performance budgets to ensure consistent response times:

### Budget Targets

- **Fast lane**: p95 < 150ms (optimized for speed)
- **Accurate lane**: p95 < 500ms (optimized for quality)
- **Warmup exclusion**: First 3 queries per process are excluded from budget calculations
- **High precision timing**: Microsecond precision using `time.perf_counter()`

### Budget Check Tool

Use the budget check mode for performance validation:

```bash
# Check current performance budgets (one-time analysis)
python tools/tail_rag_logs.py --budget-check --since 60

# Continuous budget monitoring
python tools/tail_rag_logs.py --budget-check --follow

# Extended window for better statistical accuracy
python tools/tail_rag_logs.py --budget-check --p95-window 500 --since 120
```

### Budget Status Interpretation

```
PERFORMANCE BUDGET CHECK
==================================================
Lane fast     p95=120ms  ✅ (target 150ms)
Lane accurate p95=650ms  ❌ (target 500ms, +30.0%)
==================================================
Window size: 200 events (warmup excluded)
==================================================
```

- **✅ Green**: Lane is within budget (p95 ≤ target)
- **❌ Red**: Lane exceeds budget (shows percentage over target)
- **❓ Gray**: No data available for analysis

### Performance Debugging

```bash
# Find slow operations excluding warmup
jq -r 'select(.flags.warmup != true and .stages.total_ms > 300)' logs/rag/*.jsonl

# Check warmup query behavior
jq -r 'select(.flags.warmup == true) | "\(.ts) lane=\(.lane) total=\(.stages.total_ms)ms"' logs/rag/*.jsonl

# Lane-specific performance analysis
jq -r 'select(.lane=="fast" and .flags.warmup != true) | .stages.total_ms' logs/rag/*.jsonl | sort -n
jq -r 'select(.lane=="accurate" and .flags.warmup != true) | .stages.total_ms' logs/rag/*.jsonl | sort -n

# Timing breakdown for budget violations
jq -r 'select(.lane=="fast" and .flags.warmup != true and .stages.total_ms > 150)
       | "retrieve=\(.stages.retrieve_ms)ms rerank=\(.stages.rerank_ms)ms synth=\(.stages.synth_ms)ms"' \
       logs/rag/*.jsonl

# Performance trends over time
jq -r 'select(.flags.warmup != true) | "\(.ts[11:19]) \(.lane) \(.stages.total_ms)"' logs/rag/*.jsonl | tail -20
```

### Budget Alert Thresholds

Recommended alerting for performance budgets:

- **Fast lane budget violation**: p95 > 150ms for >5 minutes
- **Accurate lane budget violation**: p95 > 500ms for >5 minutes  
- **Sustained performance degradation**: Any lane >2x budget for >2 minutes
- **Warmup exclusion validation**: Ensure first 3 queries are properly tagged

### Performance Regression Detection

```bash
# Compare performance across deployments
# Before deployment
python tools/tail_rag_logs.py --budget-check --since 30 > pre_deploy.txt

# After deployment  
python tools/tail_rag_logs.py --budget-check --since 30 > post_deploy.txt

# Manual comparison of p95 values
diff pre_deploy.txt post_deploy.txt
```

### Timing Instrumentation Validation

Verify that high precision timing is working correctly:

```bash
# Check timing precision (should have decimal places)
jq -r '.stages.total_ms' logs/rag/*.jsonl | grep -E '\.' | head -5

# Validate stage timing relationships (total ≈ retrieve + rerank + synth)
jq -r 'select(.stages.total_ms != null and .stages.retrieve_ms != null) 
       | "\(.stages.total_ms) \(.stages.retrieve_ms + .stages.rerank_ms + .stages.synth_ms)"' \
       logs/rag/*.jsonl | head -5

# Warmup flag validation
jq -r '.flags.warmup' logs/rag/*.jsonl | sort | uniq -c
```

## Canon Reindex Pipeline

The Canon Reindex Pipeline automatically rebuilds vector indexes when protocol canon files change, providing statistics tracking and atomic updates.

### One-shot Reindex

```bash
# Reindex both speed and accuracy lanes
python tools/reindex.py --once

# View stats diff after reindex
python tools/reindex.py --stats
```

### Auto-reindex with File Watching

```bash
# Watch canon for changes and auto-reindex
python tools/reindex.py --watch
```

### Reindex Monitoring

```bash
# View last reindex stats diff
tail -n 1 lichen-protocol-mvp/logs/rag/reindex/*.jsonl | jq .

# Monitor recent reindex events
tail -f lichen-protocol-mvp/logs/rag/reindex/*.jsonl

# Check stones coverage after reindex
tail -n 1 lichen-protocol-mvp/logs/rag/reindex/*.jsonl | jq '.stats_diff.stones_coverage_after'

# Protocol count changes
tail -n 1 lichen-protocol-mvp/logs/rag/reindex/*.jsonl | jq '.stats_diff | {protocols_before, protocols_after, tokens_added}'
```

### Reindex Logs Schema

Reindex events are logged to `logs/rag/reindex/YYYY-MM-DD.jsonl`:

```json
{
  "ts": "2025-09-12T04:32:01Z",
  "event": "reindex", 
  "changed_files": ["aligning_investor_energy_with_the_field.json"],
  "stats_diff": {
    "protocols_before": 182,
    "protocols_after": 183,
    "stones_coverage_before": ["light-before-form", "..."],
    "stones_coverage_after": ["light-before-form", "speed-of-trust", "..."],
    "tokens_added": 1200,
    "tokens_removed": 0,
    "avg_chunk_size_before": 245.2,
    "avg_chunk_size_after": 248.1
  }
}
```

### Stones Coverage Analysis

The pipeline tracks coverage of all 10 Stones:

```bash
# Check which stones are covered in current canon
python tools/reindex.py --stats | grep "stones covered\|Missing from canon"

# Full stones coverage report
tail -n 1 logs/rag/reindex/*.jsonl | jq -r '.stats_diff.stones_coverage_after[] | "✅ " + .' && \
echo "Missing stones:" && \
tail -n 1 logs/rag/reindex/*.jsonl | jq -r '
  ["light-before-form","speed-of-trust","field-before-stones","essence-first","truth-over-comfort","energy-follows-attention","dynamics-over-content","evolutionary-edge","aligned-action","presence-over-perfection"] - .stats_diff.stones_coverage_after | .[] | "❌ " + .
'
```

### Index Directory Structure

```
lichen-chunker/
├── index/
│   ├── speed/          # Fast lane indexes (git-ignored)
│   │   ├── *.faiss
│   │   ├── *.jsonl
│   │   └── manifest.json
│   └── accuracy/       # Accurate lane indexes (git-ignored)
│       ├── *.faiss  
│       ├── *.jsonl
│       └── manifest.json
└── libs/
    └── protocol_template_schema_v1.json
```

### Troubleshooting Reindex Issues

```bash
# Check if canon path exists
ls -la ~/Desktop/Hybrid_SIS_Build/02_Canon_Exemplars/Protocol_Canon/

# Validate chunker CLI is available
python -m lichen_chunker.cli --help

# Manual chunker run for debugging
python -m lichen_chunker.cli process --profile speed --schema lichen-chunker/libs/protocol_template_schema_v1.json

# Check pre-commit vector file blocking
python tools/block_vector_files.py .vector/test.faiss

# Verify git ignores vector files  
git status --ignored | grep -E "(\.vector|lichen-chunker/index)"
```

### Git Hygiene

The pipeline enforces git hygiene to prevent committing large index files:

- `.gitignore` excludes `lichen-chunker/index/**` and `.vector/`
- Pre-commit hook blocks accidental commits of vector files
- Index files are built locally and deployed separately

### Performance Considerations

- **Reindex frequency**: Canon changes trigger immediate reindex
- **Index size**: Each lane maintains separate indexes (~100MB-1GB each)
- **Build time**: Full reindex takes 2-10 minutes depending on canon size
- **Atomic updates**: New indexes replace old ones atomically to prevent corruption
- **Debouncing**: File watcher debounces rapid changes (5 second window)

## Log Retention

- RAG logs are stored in `lichen-protocol-mvp/logs/rag/YYYY-MM-DD.jsonl`
- Reindex logs are stored in `lichen-protocol-mvp/logs/rag/reindex/YYYY-MM-DD.jsonl`
- Files are git-ignored and rotate daily
- Recommended retention: 30 days in staging, 7 days in development
- Archive old logs before they consume excessive disk space