# Lichen Workspace

This workspace contains two main projects for protocol processing and management:

## Projects

### lichen-chunker
Document chunking and indexing system with FAISS vector search capabilities.

### lichen-protocol-mvp
Complex protocol system with room-based architecture for protocol management and execution.

## 24-Protocol Manifest Generation

Generate a balanced manifest of exactly 24 protocols from the canon folder with optimal distribution across readiness stages, length buckets, stones coverage, and fields coverage.

### Generate a balanced 24-item manifest

```bash
python tools/build_manifest.py \
  --canon "~/Desktop/Hybrid_SIS_Build/02_Canon_Exemplars/Protocol_Canon" \
  --out "manifests"
```

### Copy protocols from manifest to test directory

```bash
# Copy all protocols from latest manifest to test-protocols folder
python tools/copy_manifest_protocols.py --latest

# Or specify a specific manifest file
python tools/copy_manifest_protocols.py --manifest manifests/canon_batch_2025-09-11.yaml --output test-protocols
```

### Run both lanes with the manifest (Speed then Accuracy)

```bash
# Speed lane: feed the 24 paths to process --profile speed
xargs -a <(yq '.items[].path' manifests/canon_batch_*.yaml) \
  python -m src.lichen_chunker.cli process --profile speed --schema libs/protocol_template_schema_v1.json

# Accuracy lane: same with --profile accuracy  
xargs -a <(yq '.items[].path' manifests/canon_batch_*.yaml) \
  python -m src.lichen_chunker.cli process --profile accuracy --schema libs/protocol_template_schema_v1.json
```

## Requirements

- Python 3.7+
- PyYAML (`pip install pyyaml`)
- yq (for YAML processing in shell commands)

## Usage

1. Generate a manifest using the build_manifest.py tool
2. Use the generated YAML manifest to run processing pipelines
3. The manifest ensures balanced coverage across all required dimensions

The manifest tool selects protocols based on:
- **Readiness Stages**: 8×Explore, 8×Act, 8×Integrate
- **Length buckets**: Optimized based on actual canon distribution
- **Stones coverage**: All 10 Stones with ≥2 protocols per Stone
- **Fields coverage**: At least one of each required field
- **Must-include protocols**: Hard-includes specified protocols if present
