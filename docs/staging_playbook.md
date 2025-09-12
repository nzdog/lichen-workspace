# Staging Playbook

This document provides operational procedures for managing the staging environment and ensuring system security and privacy.

## Redaction System

### Environment Control

The redaction system can be controlled via the `REDACT_LOGS` environment variable:

```bash
# Enable redaction (default - recommended for production)
export REDACT_LOGS=1

# Disable redaction (development/debugging only)
export REDACT_LOGS=0
```

### Verification on Staging

To verify redaction is working correctly on staging:

```bash
# Check for redacted tokens in logs
grep -Eo '(\[EMAIL_REDACTED\]|\[PHONE_REDACTED\]|\[NAME_REDACTED\]|\[API_KEY_REDACTED\])' logs/rag/*.jsonl | head

# Verify no raw sensitive data appears
grep -E '(john@example\.com|555-123-4567|John Smith)' logs/rag/*.jsonl || echo "✅ No raw sensitive data found"
```

### Redaction Patterns

The system redacts the following patterns:

- **Emails**: `user@domain.com` → `[EMAIL_REDACTED]`
- **Phone Numbers**: `(555) 123-4567` → `[PHONE_REDACTED]`
- **Names**: `John Smith` → `[NAME_REDACTED]`
- **SSNs**: `123-45-6789` → `[SSN_REDACTED]`
- **Credit Cards**: `4532-1234-5678-9012` → `[CARD_REDACTED]`
- **API Keys**: `sk-1234567890abcdef...` → `[API_KEY_REDACTED]`
- **URLs**: `https://api.example.com/v1/data` → `[URL_REDACTED]`

### Testing Redaction

```bash
# Test redaction functionality
cd lichen-protocol-mvp
python -c "
import os
os.environ['REDACT_LOGS'] = '1'
from hallway.redaction import redact_text
result = redact_text('Contact john@example.com or call (555) 123-4567')
print(result)
"
# Expected output: "Contact [EMAIL_REDACTED] or call [PHONE_REDACTED]"
```

## Git Hygiene

### Pre-commit Hooks

The repository includes pre-commit hooks that prevent:

- Commits of files larger than 1MB
- Commits of binary files (FAISS indexes, pickles, etc.)
- Commits of log files (`*.jsonl`, `logs/**`)
- Commits of index files (`lichen-chunker/index/**`)

### Bypassing Hooks (Owners Only)

In exceptional circumstances, hooks can be bypassed:

```bash
# Bypass pre-commit hooks (use with caution)
git commit --no-verify -m "Emergency fix - reason: [explain why bypass was necessary]"
```

**Important**: When bypassing hooks, document the reason in the PR description and ensure the bypassed content is reviewed by a team lead.

### CI Checks

The CI system automatically runs:

- Redaction unit tests
- Repository hygiene checks
- Large file detection
- Binary file detection
- .gitignore validation
- Pre-commit hook verification

## Log Management

### Log Locations

- **RAG Logs**: `lichen-protocol-mvp/logs/rag/`
- **Reindex Logs**: `lichen-protocol-mvp/logs/rag/reindex/`
- **Application Logs**: `logs/` (if any)

### Log Rotation

Logs are automatically rotated by date:
- Format: `YYYY-MM-DD.jsonl`
- Location: `logs/rag/YYYY-MM-DD.jsonl`

### Log Monitoring

```bash
# Monitor live logs
tail -f lichen-protocol-mvp/logs/rag/$(date +%Y-%m-%d).jsonl

# Check for errors
grep -i error logs/rag/*.jsonl

# Check redaction status
grep -c "\[.*_REDACTED\]" logs/rag/*.jsonl
```

## Security Procedures

### Incident Response

If sensitive data is detected in logs:

1. **Immediate**: Disable logging if necessary
   ```bash
   export RAG_OBS_ENABLED=0
   ```

2. **Investigate**: Check redaction configuration
   ```bash
   echo $REDACT_LOGS
   python -c "from hallway.redaction import get_redactor; print(get_redactor().get_redaction_stats())"
   ```

3. **Remediate**: Fix redaction patterns if needed
4. **Verify**: Re-enable logging and verify redaction works
5. **Document**: Record incident and resolution

### Regular Security Checks

Run these checks regularly:

```bash
# Check for tracked sensitive files
git ls-files | grep -E '(^|/)logs/|\.jsonl$|lichen-chunker/index/'

# Check for large files
git ls-files -s | awk '{print $4}' | xargs -I {} sh -c '[ -f {} ] && [ $(wc -c < {}) -gt 1000000 ] && echo "Large file: {}"'

# Verify .gitignore coverage
grep -E "(logs/|\.jsonl|lichen-chunker/index/)" .gitignore
```

## Troubleshooting

### Redaction Not Working

1. Check environment variable:
   ```bash
   echo $REDACT_LOGS
   ```

2. Verify redaction is enabled:
   ```bash
   python -c "from hallway.redaction import get_redactor; print('Enabled:', get_redactor().redaction_enabled)"
   ```

3. Test with known sensitive data:
   ```bash
   python -c "from hallway.redaction import redact_text; print(redact_text('john@example.com'))"
   ```

### Pre-commit Hook Issues

1. Check hook exists and is executable:
   ```bash
   ls -la .git/hooks/pre-commit
   ```

2. Test hook manually:
   ```bash
   .git/hooks/pre-commit
   ```

3. Reinstall hook if needed:
   ```bash
   chmod +x .git/hooks/pre-commit
   ```

### CI Failures

1. Check workflow status:
   ```bash
   # View workflow runs
   gh run list --workflow=redaction.yml
   ```

2. Review failure logs:
   ```bash
   # Get latest run details
   gh run view --log
   ```

3. Fix issues locally:
   ```bash
   # Run same checks locally
   pytest -q eval/tests/ hallway/tests/ -k "redaction or observability"
   ```

## Emergency Procedures

### Disable All Logging

```bash
export RAG_OBS_ENABLED=0
export REDACT_LOGS=0
# Restart services if needed
```

### Emergency Commit

```bash
# Only for critical fixes
git commit --no-verify -m "EMERGENCY: [describe issue and why bypass was necessary]"
```

### Rollback Redaction

```bash
# Disable redaction temporarily
export REDACT_LOGS=0
# Restart services
# Monitor for any sensitive data leakage
```

## Contact Information

- **Security Issues**: Contact team lead immediately
- **Redaction Problems**: Check this playbook first, then escalate
- **CI Issues**: Review workflow logs and fix locally before re-running

## Change Log

- **2025-09-12**: Initial playbook created with redaction procedures
- **2025-09-12**: Added emergency procedures and troubleshooting
