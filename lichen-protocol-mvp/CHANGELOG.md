# Changelog

All notable changes to this project will be documented in this file.

## [phase-2-staging-hardening] — 2025-09-12

### Added
- **Feature-flagged rollout**
  - RAG gated behind `RAG_ENABLED` (default fast lane).
  - Lane selection via `RAG_LANE=fast|accurate`.
  - Safe fallback path when disabled.

- **Expanded evalset**
  - 30–50 prompts covering all 10 Foundation Stones and key Fields.
  - `stone_meaning` embedded in prompts for semantic checks.
  - CI ensures coverage.

- **Observability**
  - JSONL logs per turn with lane, top-k, Stones, grounding, stage timings, p95 tracking.
  - New CLI: `tools/tail_rag_logs.py --follow` with filters.
  - `jq` recipes documented for slow turns, low grounding, accurate lane.

- **Guardrails**
  - Enforces minimum grounding threshold (default 0.25, env override).
  - Zero-hallucination fallback if threshold violated.
  - Requires citations in all outputs.
  - Refusals logged with explicit flags.

- **Performance budgets**
  - Fast lane p95 < 150ms after warmup.
  - Accurate lane p95 < 500ms after warmup.
  - `--budget-check` flag in tail tool validates targets.

- **Canon reindex pipeline**
  - Auto-reindex on canon file changes (watchdog + CLI).
  - Stats diffs logged (protocol count, tokens, Stones coverage).
  - `.vector/` and index artifacts excluded from git via `.gitignore` + pre-commit hook.

- **Security & privacy**
  - Redaction system (`REDACT_LOGS=1` default).
  - Sensitive patterns covered (emails, phones, API keys, etc.).
  - CI + hooks block logs, indexes, large binaries.

- **Operational playbook**
  - Docs updated with env vars, tail filters, guardrail jq recipes, and reindex usage.
  - Troubleshooting + incident response included.

### Summary
Phase 2 is complete. The system is now staging-ready with feature flags, evalset coverage, observability, guardrails, performance budgets, auto-reindex, and operational hardening.

## [Unreleased]
### Added
- Pre-commit hooks to validate contracts and run contract tests.
- GitHub Actions workflow to validate and test contracts on PRs.
### Changed
- Validator now enforces `$schema` as first key and treats warnings as errors (with small allowlist).
- Dependencies pinned for jsonschema/pytest/pre-commit.
