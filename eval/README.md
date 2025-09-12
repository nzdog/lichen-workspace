# Expanded RAG Evaluation System

This directory contains the expanded evaluation system for the RAG (Retrieval-Augmented Generation) pipeline, organized by Foundation Stones and Fields.

## Structure

### `prompts/` Directory
Contains YAML files organized by Foundation Stones, each with multiple evaluation prompts:

- **10 Foundation Stones** (≥3 prompts each):
  - `light_essence_before_form.yaml` - 4 prompts
  - `trust_speed_of_trust.yaml` - 4 prompts  
  - `stewardship_over_ownership.yaml` - 4 prompts
  - `clarity_over_cleverness.yaml` - 4 prompts
  - `presence_over_urgency.yaml` - 4 prompts
  - `nothing_forced_nothing_withheld.yaml` - 4 prompts
  - `no_contortion_acceptance_not_contorted_for.yaml` - 4 prompts
  - `integrity_drives_growth.yaml` - 4 prompts
  - `wholeness_whole_system_respected.yaml` - 4 prompts
  - `system_walks_with_us.yaml` - 4 prompts

- **Additional Field-specific files**:
  - `rhythm_and_timing.yaml` - 3 prompts
  - `conflict_resolution.yaml` - 3 prompts
  - `change_management.yaml` - 3 prompts
  - `energy_management.yaml` - 2 prompts

### **24 Fields Covered** (≥1 prompt each):
- `self-awareness` (10 prompts)
- `team-management` (5 prompts)
- `leadership` (3 prompts)
- `decision-making` (3 prompts)
- `conflict-resolution` (4 prompts)
- `rhythm-and-timing` (3 prompts)
- `change-management` (3 prompts)
- `business-strategy` (2 prompts)
- `team-building` (2 prompts)
- `energy-management` (2 prompts)
- `communication` (1 prompt)
- `problem-solving` (1 prompt)
- `product-development` (1 prompt)
- `resource-management` (1 prompt)
- `authenticity` (1 prompt)
- `collaboration` (1 prompt)
- `ethical-leadership` (1 prompt)
- `fundraising` (1 prompt)
- `intuition` (1 prompt)
- `mindfulness` (1 prompt)
- `organizational-development` (1 prompt)
- `personal-effectiveness` (1 prompt)
- `stress-management` (1 prompt)
- `systems-thinking` (1 prompt)

## Usage

### Run Evaluation
```bash
# Use YAML prompts (default)
python3 -m eval.run_eval --prompts-dir eval/prompts --outdir eval/out

# Use legacy JSON evalset
python3 -m eval.run_eval --evalset eval/evalset.json --use-yaml=False
```

### Test System
```bash
python3 eval/test_eval_system.py
```

### Validate Prompts
```bash
# Validate YAML prompt set against registry
python3 eval/tools/validate_prompts.py

# Run comprehensive tests
pytest -q eval/tests
```

## Output Files

The evaluation generates separate results for both lanes:

- `eval/out/summary_fast.json` - Fast lane metrics
- `eval/out/summary_accurate.json` - Accurate lane metrics  
- `eval/out/records_fast.jsonl` - Fast lane detailed records
- `eval/out/records_accurate.jsonl` - Accurate lane detailed records

## Prompt Format

Each prompt in the YAML files contains:

```yaml
prompts:
  - query_id: "stone-001"
    prompt: "How do I start from essence before form when building a new product?"
    stone: "light-before-form"
    stone_meaning: |
      We protect the soul of the system before shaping its structure. We trust essence to lead design—not the other way around.
    field: "product-development"
    difficulty: "medium"
    assertions:
      - "Should emphasize starting with core purpose and values"
      - "Should mention avoiding feature-first thinking"
      - "Should reference understanding the deeper need being served"
    gold_doc_ids:
      - "the_leadership_im_actually_carrying"
      - "presence_is_productivity"
    top_k_for_generation: 8
```

### Stones Registry

The system includes a canonical Foundation Stones registry (`eval/stones.yaml`) with:

- **10 Foundation Stones** with exact meanings from foundation documentation
- **Semantic alignment checks** using `must_haves` and `red_flags` for each Stone
- **Automatic validation** of `stone_meaning` against the registry

### Semantic Alignment

The evaluation system now includes semantic alignment checking:

- **Positive alignment**: Checks for `must_haves` phrases in generated answers
- **Negative alignment**: Detects `red_flags` phrases that indicate misalignment
- **Assertion-based checking**: Supports `must_reference_stone_meaning: true` assertions
- **Per-Stone metrics**: Tracks alignment success/failure rates by Stone

## Metrics Evaluated

- **Retrieval Metrics**: Precision@5, Recall@20, MRR@10, nDCG@10, Coverage
- **Performance Metrics**: Latency p95, Diversity (unique docs in top-8)
- **Quality Metrics**: Stones Alignment, Grounding Score (1-5), Hallucination Rate

## Coverage Verification

The system ensures:
- ✅ **10 Foundation Stones** with ≥3 prompts each
- ✅ **24 Fields** with ≥1 prompt each  
- ✅ **51 total prompts** across all categories
- ✅ **Both lanes evaluated** (fast and accurate)
- ✅ **Separate output files** for each lane
- ✅ **CI compatibility** with comprehensive test suite
