# Makefile for RAG Pipeline
# Headless two-lane pipeline with per-lane model control

.PHONY: help embed-fast embed-accurate catalog clean logs test-eval auto-label

# Default target
help:
	@echo "RAG Pipeline Build Targets"
	@echo "=========================="
	@echo "embed-fast     - Build fast lane indices (480 char windows)"
	@echo "embed-accurate - Build accurate lane indices (1000 char windows)"
	@echo "catalog        - Build protocol catalog with embeddings"
	@echo "all            - Build both lanes and catalog"
	@echo "clean          - Clean build artifacts"
	@echo "logs           - Show recent build logs"
	@echo "test-eval      - Run evaluation with new pipeline"
	@echo "auto-label     - Auto-label eval dataset using protocol catalog"
	@echo ""
	@echo "Environment Variables:"
	@echo "EMBED_MODEL_FAST      - Fast lane embedding model (default: sentence-transformers/all-MiniLM-L6-v2)"
	@echo "EMBED_MODEL_ACCURATE  - Accurate lane embedding model (default: sentence-transformers/all-MiniLM-L6-v2)"
	@echo "CROSS_ENCODER_MODEL   - Cross-encoder model (optional)"
	@echo "ROUTER_HARD_GATE      - Router gating (0=soft, 1=hard, default: 1)"
	@echo "RAG_STRATEGY          - Retrieval strategy (default: protocol_first_hybrid)"

# Create necessary directories
data/chunks data/indexes logs:
	mkdir -p $@

# Fast lane pipeline
embed-fast: data/chunks data/indexes
	@echo "🚀 Building fast lane indices..."
	@echo "Model: $${EMBED_MODEL_FAST:-sentence-transformers/all-MiniLM-L6-v2}"
	@echo "Window: 480 chars, Overlap: 50 chars"
	@echo ""
	
	@echo "📄 Chunking protocols..."
	python3 scripts/chunk_canon.py \
		--in "protocols/**/*.json" \
		--out data/chunks/chunks_fast.jsonl \
		--window 480 --overlap 50 --by-theme \
		--add-meta protocol_id,title,theme_name,stones,fields,bridges,tags
	@echo "🔢 Embedding chunks..."
	python3 scripts/embed_chunks.py \
		--in data/chunks/chunks_fast.jsonl \
		--out data/indexes/vecs_fast.faiss \
		--stats data/indexes/vecs_fast.stats.json \
		--model "$${EMBED_MODEL_FAST:-sentence-transformers/all-MiniLM-L6-v2}" \
		--batch-size 256 --device auto --verify
	
	@echo "✅ Fast lane build complete!"

# Accurate lane pipeline  
embed-accurate: data/chunks data/indexes
	@echo "🎯 Building accurate lane indices..."
	@echo "Model: $${EMBED_MODEL_ACCURATE:-sentence-transformers/all-MiniLM-L6-v2}"
	@echo "Window: 1000 chars, Overlap: 120 chars"
	@echo ""
	
	@echo "📄 Chunking protocols..."
	python3 scripts/chunk_canon.py \
		--in "protocols/**/*.json" \
		--out data/chunks/chunks_accurate.jsonl \
		--window 1000 --overlap 120 --by-theme \
		--add-meta protocol_id,title,theme_name,stones,fields,bridges,tags
	@echo "🔢 Embedding chunks..."
	python3 scripts/embed_chunks.py \
		--in data/chunks/chunks_accurate.jsonl \
		--out data/indexes/vecs_accurate.faiss \
		--stats data/indexes/vecs_accurate.stats.json \
		--model "$${EMBED_MODEL_ACCURATE:-sentence-transformers/all-MiniLM-L6-v2}" \
		--batch-size 128 --device auto --verify
	
	@echo "✅ Accurate lane build complete!"

# Protocol catalog
catalog:
	@echo "📚 Building protocol catalog..."
	@echo "Model: $${EMBED_MODEL_ACCURATE:-sentence-transformers/all-MiniLM-L6-v2}"
	@echo ""
	
	python3 scripts/build_protocol_catalog.py \
		--in "protocols/**/*.json" \
		--stones Foundation_Stones_of_the_System.txt \
		--out data/protocol_catalog.json \
		--model "$${EMBED_MODEL_ACCURATE:-sentence-transformers/all-MiniLM-L6-v2}"
	
	@echo "✅ Protocol catalog build complete!"

# Build all components
all: embed-fast embed-accurate catalog
	@echo "🎉 All components built successfully!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Test with: make test-eval"
	@echo "2. Or run evaluation manually with new pipeline"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf data/chunks/*.jsonl
	rm -rf data/indexes/*.faiss
	rm -rf data/indexes/*.json
	rm -rf data/indexes/*.jsonl
	rm -f data/protocol_catalog.json
	rm -rf logs/*.json
	@echo "✅ Clean complete!"

# Show recent logs
logs:
	@echo "📋 Recent build logs:"
	@echo "===================="
	@if [ -d logs ]; then \
		find logs -name "*.json" -type f -exec basename {} \; | sort -r | head -10; \
	else \
		echo "No logs found"; \
	fi

# Test evaluation with new pipeline
test-eval:
	@echo "🧪 Testing evaluation with new pipeline..."
	@echo ""
	@echo "Configuration:"
	@echo "  FAST_INDEX_PATH: $${FAST_INDEX_PATH:-data/indexes/vecs_fast.faiss}"
	@echo "  ACCURATE_INDEX_PATH: $${ACCURATE_INDEX_PATH:-data/indexes/vecs_accurate.faiss}"
	@echo "  PROTOCOL_CATALOG_PATH: $${PROTOCOL_CATALOG_PATH:-data/protocol_catalog.json}"
	@echo "  RAG_STRATEGY: $${RAG_STRATEGY:-protocol_first_hybrid}"
	@echo "  ROUTER_HARD_GATE: $${ROUTER_HARD_GATE:-0}"
	@echo ""
	
	cd eval && python3 run_eval.py \
		--evalset datasets/founder_early.jsonl \
		--outdir out \
		--debug-retrieval

# Development helpers
dev-setup:
	@echo "🛠️  Setting up development environment..."
	pip install -r requirements-dev.txt
	python3 -c "import sentence_transformers; print('✅ sentence-transformers available')"
	python3 -c "import faiss; print('✅ faiss-cpu available')"
	python3 -c "import yaml; print('✅ PyYAML available')"
	python3 -c "import tqdm; print('✅ tqdm available')"
	@echo "✅ Development setup complete!"

# Validate configuration
validate-config:
	@echo "🔍 Validating configuration..."
	python3 -c "from rag.config import resolve_config, validate_config, print_config_summary; config = resolve_config(); issues = validate_config(config); print_config_summary(config); exit(1 if issues else 0)"

# Inspect indices
inspect-fast:
	@echo "🔍 Inspecting fast index..."
	python3 rag/index/faiss_store.py data/indexes/vecs_fast.faiss data/indexes/vecs_fast.stats.json

inspect-accurate:
	@echo "🔍 Inspecting accurate index..."
	python3 rag/index/faiss_store.py data/indexes/vecs_accurate.faiss data/indexes/vecs_accurate.stats.json

# Quick test of hybrid retriever
test-hybrid:
	@echo "🧪 Testing hybrid retriever..."
	python3 test_hybrid.py

# Auto-label eval dataset using protocol catalog
auto-label:
	python3 scripts/auto_label_eval.py --in eval/datasets/founder_early.jsonl --catalog data/protocol_catalog.json --out eval/datasets/founder_early_labeled.jsonl --topk 2 --min-score 62
