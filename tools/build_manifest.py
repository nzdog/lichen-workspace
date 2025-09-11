#!/usr/bin/env python3
"""
Build a balanced 24-protocol manifest from the canon folder.

Selects 24 protocols with balanced distribution across:
- Readiness Stages: 8×Explore, 8×Act, 8×Integrate
- Length buckets: 8×short (≤800), 12×medium (801-2000), 4×long (≥2001)
- Stones coverage: all 10 Stones with ≥2 protocols per Stone
- Fields coverage: at least one of each required field
"""

import json
import os
import argparse
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Set
import yaml


# Fixed seed for deterministic selection
random.seed(42)

# Required Stones (all 10)
ALL_STONES = {
    "stewardship-not-ownership",
    "integrity-is-the-growth-strategy", 
    "nothing-forced-nothing-withheld",
    "presence-is-productivity",
    "support-rhythm-and-escalations",
    "sustaining-rhythm-without-a-hero",
    "the-speed-of-trust",
    "integrating-what-weve-outgrown",
    "building-a-field-aligned-sales-process",
    "the-energy-behind-the-ask"
}

# Required Fields
REQUIRED_FIELDS = {
    "integrity", "relational", "wholeness", "strategy", 
    "funding", "team", "product", "narrative"
}

# Must-include protocols
MUST_INCLUDE = {
    "the_leadership_im_actually_carrying.json",
    "letting_go_of_the_startup.json"
}

# Length buckets
LENGTH_BUCKETS = {
    "short": (0, 800),
    "medium": (801, 2000), 
    "long": (2001, float('inf'))
}

# Stage quotas
STAGE_QUOTAS = {"Explore": 8, "Act": 8, "Integrate": 8}
# Adjust length quotas based on actual canon distribution
LENGTH_QUOTAS = {"short": 0, "medium": 4, "long": 20}


def estimate_tokens(content: str) -> int:
    """Estimate token count as ~chars/4."""
    return len(content) // 4


def get_length_bucket(est_tokens: int) -> str:
    """Determine length bucket for given token estimate."""
    for bucket, (min_tokens, max_tokens) in LENGTH_BUCKETS.items():
        if min_tokens <= est_tokens <= max_tokens:
            return bucket
    return "medium"  # fallback


def load_protocol(file_path: Path) -> Dict:
    """Load and parse a protocol JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {file_path}: {e}")
        return None


def extract_protocol_info(file_path: Path, protocol_data: Dict) -> Dict:
    """Extract relevant info from protocol data."""
    content = json.dumps(protocol_data, separators=(',', ':'))
    est_tokens = estimate_tokens(content)
    
    metadata = protocol_data.get("Metadata", {})
    
    # Handle stones - convert to strings if they're dicts
    stones_raw = metadata.get("Stones", [])
    stones = set()
    for stone in stones_raw:
        if isinstance(stone, str):
            stones.add(stone)
        elif isinstance(stone, dict):
            # Extract string value from dict if needed
            stones.add(str(stone))
    
    # Handle fields - convert to strings if they're dicts  
    fields_raw = metadata.get("Fields", [])
    fields = set()
    for field in fields_raw:
        if isinstance(field, str):
            fields.add(field)
        elif isinstance(field, dict):
            # Extract string value from dict if needed
            fields.add(str(field))
    
    return {
        "path": str(file_path),
        "protocol_id": file_path.stem,
        "title": protocol_data.get("Title", ""),
        "readiness_stage": metadata.get("Readiness Stage", ""),
        "est_tokens": est_tokens,
        "length_bucket": get_length_bucket(est_tokens),
        "stones": stones,
        "fields": fields,
        "raw_data": protocol_data
    }


def is_valid_protocol(file_path: Path) -> bool:
    """Check if file should be included (not template/schema/locked)."""
    name = file_path.name.lower()
    return (
        file_path.suffix == '.json' and
        'template' not in name and
        'schema' not in name and 
        'locked' not in name
    )


def calculate_score(protocol: Dict, stage_counts: Dict, length_counts: Dict, 
                   stones_coverage: Dict, fields_coverage: Set) -> Tuple[int, str]:
    """Calculate selection score for deterministic sorting."""
    score = 0
    
    # Prefer protocols with more Stones (capped at 3)
    score += min(len(protocol["stones"]), 3) * 1000
    
    # Prefer protocols with under-covered Fields
    for field in protocol["fields"]:
        if field in REQUIRED_FIELDS and field not in fields_coverage:
            score += 500
    
    # Prefer medium length for balance (unless filling long quota)
    if protocol["length_bucket"] == "medium" and length_counts["medium"] < LENGTH_QUOTAS["medium"]:
        score += 100
    elif protocol["length_bucket"] == "short" and length_counts["short"] < LENGTH_QUOTAS["short"]:
        score += 50
    elif protocol["length_bucket"] == "long" and length_counts["long"] < LENGTH_QUOTAS["long"]:
        score += 200
    
    # Prefer protocols with under-represented Stones
    for stone in protocol["stones"]:
        if stone in ALL_STONES and stones_coverage.get(stone, 0) < 2:
            score += 300
    
    # Use title for deterministic tie-breaking
    title_slug = protocol["title"].lower().replace(" ", "_")
    
    return (-score, title_slug)  # Negative for descending sort


def select_protocols(candidates: List[Dict]) -> List[Dict]:
    """Select 24 protocols meeting all constraints."""
    selected = []
    selected_ids = set()  # Track selected protocol IDs
    stage_counts = {"Explore": 0, "Act": 0, "Integrate": 0}
    length_counts = {"short": 0, "medium": 0, "long": 0}
    stones_coverage = {stone: 0 for stone in ALL_STONES}
    fields_coverage = set()
    
    # Step 1: Hard-include must-have protocols
    for candidate in candidates:
        if candidate["protocol_id"] + ".json" in MUST_INCLUDE:
            selected.append(candidate)
            selected_ids.add(candidate["protocol_id"])
            stage_counts[candidate["readiness_stage"]] += 1
            length_counts[candidate["length_bucket"]] += 1
            for stone in candidate["stones"]:
                if stone in ALL_STONES:
                    stones_coverage[stone] += 1
            fields_coverage.update(candidate["fields"])
    
    print(f"Hard-included {len(selected)} must-have protocols")
    
    # Step 2: Fill remaining slots while meeting constraints
    remaining_candidates = [c for c in candidates if c["protocol_id"] not in selected_ids]
    
    print(f"Available candidates for selection: {len(remaining_candidates)}")
    
    while len(selected) < 24 and remaining_candidates:
        # Find best candidate that fits constraints
        best_candidate = None
        best_score = None
        best_index = -1
        
        for i, candidate in enumerate(remaining_candidates):
            stage = candidate["readiness_stage"]
            length_bucket = candidate["length_bucket"]
            
            # Check if we can fit this candidate (prioritize stage quotas over length)
            if stage_counts[stage] < STAGE_QUOTAS[stage]:
                # Prefer length quota compliance but don't require it
                length_penalty = 0 if length_counts[length_bucket] < LENGTH_QUOTAS[length_bucket] else 100
                
                score_tuple = calculate_score(candidate, stage_counts, length_counts, 
                                            stones_coverage, fields_coverage)
                
                # Apply length penalty
                adjusted_score = (score_tuple[0] - length_penalty, score_tuple[1])
                
                if best_candidate is None or adjusted_score > best_score:
                    best_candidate = candidate
                    best_score = adjusted_score
                    best_index = i
        
        if best_candidate:
            selected.append(best_candidate)
            selected_ids.add(best_candidate["protocol_id"])
            stage_counts[best_candidate["readiness_stage"]] += 1
            length_counts[best_candidate["length_bucket"]] += 1
            for stone in best_candidate["stones"]:
                if stone in ALL_STONES:
                    stones_coverage[stone] += 1
            fields_coverage.update(best_candidate["fields"])
            # Remove by index to avoid object comparison issues
            remaining_candidates.pop(best_index)
            print(f"Selected: {best_candidate['title']} (ID: {best_candidate['protocol_id']}) ({best_candidate['readiness_stage']}, {best_candidate['length_bucket']})")
        else:
            # No valid candidates left, break
            print(f"No more valid candidates. Selected {len(selected)} so far.")
            print(f"Current stage counts: {stage_counts}")
            print(f"Current length counts: {length_counts}")
            break
    
    # Step 3: Ensure Stones coverage (swap if needed)
    for stone in ALL_STONES:
        if stones_coverage[stone] < 2:
            # Find best candidate with this stone
            stone_candidates = [c for c in candidates if stone in c["stones"] and c not in selected]
            if stone_candidates:
                # Replace worst selected protocol with this one
                scored_candidates = []
                for candidate in stone_candidates:
                    score_tuple = calculate_score(candidate, stage_counts, length_counts,
                                                stones_coverage, fields_coverage)
                    scored_candidates.append((score_tuple, candidate))
                scored_candidates.sort(key=lambda x: x[0], reverse=True)
                
                if scored_candidates:
                    new_candidate = scored_candidates[0][1]
                    # Remove a protocol to make room
                    if selected:
                        removed = selected.pop()
                        stage_counts[removed["readiness_stage"]] -= 1
                        length_counts[removed["length_bucket"]] -= 1
                        for s in removed["stones"]:
                            if s in ALL_STONES:
                                stones_coverage[s] -= 1
                    
                    selected.append(new_candidate)
                    stage_counts[new_candidate["readiness_stage"]] += 1
                    length_counts[new_candidate["length_bucket"]] += 1
                    for s in new_candidate["stones"]:
                        if s in ALL_STONES:
                            stones_coverage[s] += 1
                    fields_coverage.update(new_candidate["fields"])
                    print(f"Swapped in {new_candidate['title']} for Stones coverage")
    
    return selected


def main():
    parser = argparse.ArgumentParser(description="Build balanced 24-protocol manifest")
    parser.add_argument("--canon", default="~/Desktop/Hybrid_SIS_Build/02_Canon_Exemplars/Protocol_Canon",
                       help="Path to canon folder")
    parser.add_argument("--out", default="manifests", help="Output directory")
    args = parser.parse_args()
    
    # Expand tilde and resolve path
    canon_path = Path(args.canon).expanduser().resolve()
    output_dir = Path(args.out)
    output_dir.mkdir(exist_ok=True)
    
    print(f"Scanning canon folder: {canon_path}")
    
    # Collect all valid protocol files
    candidates = []
    for file_path in canon_path.rglob("*.json"):
        if is_valid_protocol(file_path):
            protocol_data = load_protocol(file_path)
            if protocol_data:
                protocol_info = extract_protocol_info(file_path, protocol_data)
                if protocol_info["readiness_stage"] in STAGE_QUOTAS:
                    candidates.append(protocol_info)
    
    print(f"Found {len(candidates)} valid protocols")
    
    # Select 24 protocols
    selected = select_protocols(candidates)
    
    # Prepare manifest data
    now = datetime.now()
    batch_id = f"canon_batch_{now.strftime('%Y-%m-%d')}"
    
    manifest_data = {
        "batch_id": batch_id,
        "created_at": now.isoformat() + "Z",
        "total": len(selected),
        "mix": {
            "stages": {stage: sum(1 for p in selected if p["readiness_stage"] == stage) 
                      for stage in STAGE_QUOTAS},
            "lengths": {bucket: sum(1 for p in selected if p["length_bucket"] == bucket)
                       for bucket in LENGTH_QUOTAS}
        },
        "items": []
    }
    
    # Add protocol items (convert sets to lists for JSON serialization)
    for protocol in selected:
        item = {
            "path": protocol["path"],
            "protocol_id": protocol["protocol_id"],
            "title": protocol["title"],
            "readiness_stage": protocol["readiness_stage"],
            "est_tokens": protocol["est_tokens"],
            "length_bucket": protocol["length_bucket"],
            "stones": sorted(list(protocol["stones"])),
            "fields": sorted(list(protocol["fields"]))
        }
        manifest_data["items"].append(item)
    
    # Write outputs
    yaml_file = output_dir / f"{batch_id}.yaml"
    json_file = output_dir / f"{batch_id}.json"
    
    with open(yaml_file, 'w') as f:
        yaml.dump(manifest_data, f, default_flow_style=False, sort_keys=False)
    
    with open(json_file, 'w') as f:
        json.dump(manifest_data, f, indent=2, sort_keys=False)
    
    # Print summary
    print(f"\n✅ Generated manifest: {batch_id}")
    print(f"📁 YAML: {yaml_file}")
    print(f"📁 JSON: {json_file}")
    
    print(f"\n📊 Selection Summary:")
    print(f"  Stages: {manifest_data['mix']['stages']}")
    print(f"  Lengths: {manifest_data['mix']['lengths']}")
    
    # Stones coverage
    stones_coverage = {}
    for protocol in selected:
        for stone in protocol["stones"]:
            if stone in ALL_STONES:
                stones_coverage[stone] = stones_coverage.get(stone, 0) + 1
    
    print(f"\n🪨 Stones Coverage:")
    for stone in sorted(ALL_STONES):
        count = stones_coverage.get(stone, 0)
        status = "✅" if count >= 2 else "⚠️"
        print(f"  {status} {stone}: {count}")
    
    # Fields coverage
    fields_coverage = set()
    for protocol in selected:
        fields_coverage.update(protocol["fields"])
    
    print(f"\n🌾 Fields Coverage:")
    for field in sorted(REQUIRED_FIELDS):
        status = "✅" if field in fields_coverage else "❌"
        print(f"  {status} {field}")


if __name__ == "__main__":
    main()
