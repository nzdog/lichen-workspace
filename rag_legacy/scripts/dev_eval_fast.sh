#!/bin/bash

# Development script for fast lane evaluation with debug logging

echo "=== Fast Lane Evaluation with Debug ==="

# Unset any embedding model environment variables
unset RAG_EMBEDDING_MODEL
unset RAG_ACCURATE_EMBEDDING_MODEL
unset RAG_FAST_EMBEDDING_MODEL
unset RAG_FAST_EMBED
unset RAG_ACCURATE_EMBED

# Set tokenizers parallelism to false
export TOKENIZERS_PARALLELISM=false

# Run the evaluation with debug logging
echo "Running fast lane evaluation with debug logging..."
python3 -m eval.run_eval --evalset eval/datasets/founder_early.jsonl --outdir eval/out --debug-retrieval

# Show the last 60 lines of the retrieval log
echo ""
echo "=== Last 60 lines of retrieval log ==="
if [ -d "logs" ]; then
    latest_log=$(ls -t logs/retrieval_*.log 2>/dev/null | head -1)
    if [ -n "$latest_log" ]; then
        tail -60 "$latest_log"
    else
        echo "No retrieval log found"
    fi
else
    echo "No logs directory found"
fi

echo ""
echo "=== Fast lane evaluation complete ==="
