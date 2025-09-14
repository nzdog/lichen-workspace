# Model Swap Rollback Guide

This guide explains how to safely rollback model swaps in the RAG system when issues are detected.

## Overview

The RAG system supports configurable embedding and reranker models per lane (fast/accurate) through:
- **Configuration file**: `config/models.yaml` (default models)
- **Environment variables**: `RAG_FAST_EMBED`, `RAG_FAST_RERANK`, `RAG_ACCURATE_EMBED`, `RAG_ACCURATE_RERANK` (overrides)

## Rollback Procedures

### 1. Environment Variable Rollback

If you used environment variables to override models:

```bash
# Remove environment variable overrides
unset RAG_FAST_EMBED
unset RAG_FAST_RERANK
unset RAG_ACCURATE_EMBED
unset RAG_ACCURATE_RERANK

# Or set them back to previous values
export RAG_FAST_EMBED="sentence-transformers/all-MiniLM-L6-v2"
export RAG_FAST_RERANK=""
export RAG_ACCURATE_EMBED="sentence-transformers/all-mpnet-base-v2"
export RAG_ACCURATE_RERANK="cross-encoder/ms-marco-electra-base"
```

### 2. Configuration File Rollback

If you modified `config/models.yaml`:

```bash
# Restore from git
git checkout HEAD -- config/models.yaml

# Or manually edit the file to restore previous values
```

### 3. Validate Rollback

After rolling back, validate that the system is working correctly:

```bash
# Run the dry-run tool to compare current vs. previous models
python tools/model_swap_dry_run.py \
  --lane fast \
  --new-embed "sentence-transformers/all-MiniLM-L6-v2" \
  --queries eval/data/test_queries.jsonl \
  --k 10 \
  --outdir /tmp/rollback_validation

# Check the generated report for expected behavior
cat /tmp/rollback_validation/report.md
```

## Risk Assessment Checklist

Before rolling back, consider these risks:

### ✅ Index Compatibility
- [ ] **Vector dimensions match**: New embedding model must produce same dimension vectors as the index
- [ ] **Index format compatibility**: FAISS index format is compatible with the rolled-back model
- [ ] **Metadata compatibility**: Document metadata format hasn't changed

### ✅ Latency Budget
- [ ] **Response time impact**: Rollback doesn't exceed latency budgets
- [ ] **Resource usage**: Model memory/CPU requirements are acceptable
- [ ] **Batch processing**: Embedding batch sizes are appropriate

### ✅ Evaluation Gates
- [ ] **Quality metrics**: Rollback maintains minimum quality thresholds
- [ ] **A/B test results**: Previous evaluation results support the rollback
- [ ] **User feedback**: No critical user complaints about the rolled-back models

### ✅ Dependencies
- [ ] **Model availability**: Rolled-back models are still available/downloadable
- [ ] **Library versions**: Required ML libraries support the rolled-back models
- [ ] **Hardware requirements**: System has sufficient resources for the models

## Emergency Rollback

For critical issues requiring immediate rollback:

### Quick Environment Override
```bash
# Set environment variables to known-good models
export RAG_FAST_EMBED="sentence-transformers/all-MiniLM-L6-v2"
export RAG_FAST_RERANK=""
export RAG_ACCURATE_EMBED="sentence-transformers/all-mpnet-base-v2"
export RAG_ACCURATE_RERANK="cross-encoder/ms-marco-electra-base"

# Restart the application/service
```

### Configuration File Emergency Edit
```bash
# Edit config/models.yaml to restore defaults
cat > config/models.yaml << 'EOF'
fast:
  embed_model: sentence-transformers/all-MiniLM-L6-v2
  reranker_model: null

accurate:
  embed_model: sentence-transformers/all-mpnet-base-v2
  reranker_model: cross-encoder/ms-marco-electra-base
EOF
```

## Monitoring After Rollback

After rolling back, monitor these metrics:

### Performance Metrics
- **Latency**: Response times should return to baseline
- **Throughput**: Request processing rates should normalize
- **Resource usage**: CPU/memory usage should return to expected levels

### Quality Metrics
- **Retrieval quality**: Use the dry-run tool to validate result quality
- **User satisfaction**: Monitor user feedback and engagement
- **Error rates**: Check for any increase in retrieval or generation errors

### System Health
- **Log analysis**: Review logs for any new errors or warnings
- **Observability**: Check RAG observability logs for model usage patterns
- **Dependencies**: Verify all model dependencies are working correctly

## Troubleshooting

### Common Issues

#### Model Loading Failures
```bash
# Check if models are available
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Clear model cache if needed
rm -rf ~/.cache/torch/sentence_transformers/
```

#### Dimension Mismatches
```bash
# Verify embedding dimensions
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
print(f'Dimensions: {model.get_sentence_embedding_dimension()}')
"
```

#### Index Compatibility Issues
```bash
# Check index metadata
python -c "
import json
with open('.vector/fast.stats.json', 'r') as f:
    stats = json.load(f)
    print(f'Index dimensions: {stats.get(\"dim\")}')
    print(f'Model used: {stats.get(\"model_name\")}')
"
```

### Getting Help

If rollback issues persist:

1. **Check logs**: Review application and RAG logs for error details
2. **Run diagnostics**: Use the dry-run tool to identify specific issues
3. **Validate configuration**: Ensure all model IDs and paths are correct
4. **Test in isolation**: Run a minimal test to isolate the problem
5. **Contact team**: Escalate to the RAG/ML team if needed

## Prevention

To avoid future rollback issues:

1. **Always test first**: Use the dry-run tool before deploying model changes
2. **Document changes**: Keep track of model changes and their rationale
3. **Monitor closely**: Watch metrics immediately after model swaps
4. **Have rollback plan**: Always have a rollback strategy before making changes
5. **Gradual rollout**: Consider gradual rollout for major model changes

## Related Documentation

- [Model Configuration Guide](config/models.yaml) - Model configuration reference
- [Dry Run Tool](tools/model_swap_dry_run.py) - Model comparison tool
- [RAG Observability](lichen-protocol-mvp/hallway/rag_observability.py) - Monitoring and logging
- [RAG Adapter](lichen-protocol-mvp/hallway/adapters/rag_adapter.py) - Core RAG implementation
