#!/usr/bin/env python3
"""
Test script to verify the expanded evaluation system works correctly.
"""

import os
import sys
import yaml
import glob
import json
from pathlib import Path

def test_yaml_loading():
    """Test that YAML files can be loaded correctly."""
    print("Testing YAML loading...")
    
    prompts_dir = "eval/prompts"
    yaml_files = glob.glob(os.path.join(prompts_dir, "*.yaml"))
    
    assert len(yaml_files) > 0, "No YAML files found in eval/prompts/"
    print(f"✓ Found {len(yaml_files)} YAML files")
    
    total_prompts = 0
    stones = set()
    fields = set()
    
    for yaml_file in yaml_files:
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
            assert 'prompts' in data, f"No 'prompts' key in {yaml_file}"
            
            for prompt in data['prompts']:
                assert 'query_id' in prompt, f"Missing query_id in {yaml_file}"
                assert 'prompt' in prompt, f"Missing prompt in {yaml_file}"
                assert 'stone' in prompt, f"Missing stone in {yaml_file}"
                assert 'field' in prompt, f"Missing field in {yaml_file}"
                assert 'difficulty' in prompt, f"Missing difficulty in {yaml_file}"
                assert 'assertions' in prompt, f"Missing assertions in {yaml_file}"
                
                stones.add(prompt['stone'])
                fields.add(prompt['field'])
                total_prompts += 1
    
    print(f"✓ Loaded {total_prompts} prompts total")
    print(f"✓ Found {len(stones)} unique stones")
    print(f"✓ Found {len(fields)} unique fields")
    
    # Check coverage requirements
    assert len(stones) >= 10, f"Need at least 10 stones, found {len(stones)}"
    assert len(fields) >= 10, f"Need at least 10 fields, found {len(fields)}"
    
    # Check minimum prompts per stone (≥3 each)
    stone_counts = {}
    for yaml_file in yaml_files:
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
            for prompt in data['prompts']:
                stone = prompt['stone']
                stone_counts[stone] = stone_counts.get(stone, 0) + 1
    
    for stone, count in stone_counts.items():
        assert count >= 3, f"Stone '{stone}' has only {count} prompts, need ≥3"
    
    print(f"✓ All stones have ≥3 prompts")
    
    # Check minimum prompts per field (≥1 each)
    field_counts = {}
    for yaml_file in yaml_files:
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
            for prompt in data['prompts']:
                field = prompt['field']
                field_counts[field] = field_counts.get(field, 0) + 1
    
    for field, count in field_counts.items():
        assert count >= 1, f"Field '{field}' has only {count} prompts, need ≥1"
    
    print(f"✓ All fields have ≥1 prompts")
    
    return total_prompts, stones, fields

def test_eval_output():
    """Test that evaluation output files are created correctly."""
    print("\nTesting evaluation output...")
    
    # Check that output directory exists
    out_dir = Path("eval/out")
    assert out_dir.exists(), "eval/out directory does not exist"
    
    # Check that summary files exist
    summary_fast = out_dir / "summary_fast.json"
    summary_accurate = out_dir / "summary_accurate.json"
    
    assert summary_fast.exists(), "summary_fast.json not found"
    assert summary_accurate.exists(), "summary_accurate.json not found"
    
    # Check that records files exist
    records_fast = out_dir / "records_fast.jsonl"
    records_accurate = out_dir / "records_accurate.jsonl"
    
    assert records_fast.exists(), "records_fast.jsonl not found"
    assert records_accurate.exists(), "records_accurate.jsonl not found"
    
    # Check summary file structure
    with open(summary_fast, 'r') as f:
        summary = json.load(f)
        required_keys = [
            "lane", "num_queries", "precision_at_5", "recall_at_20", 
            "mrr_at_10", "ndcg_at_10", "coverage", "latency_ms_p95",
            "diversity_avg_top8", "stones_alignment", "grounding_1to5", "hallucination_rate"
        ]
        for key in required_keys:
            assert key in summary, f"Missing key '{key}' in summary_fast.json"
    
    print("✓ Summary files have correct structure")
    
    # Check that both lanes processed the same number of queries
    with open(summary_fast, 'r') as f:
        fast_summary = json.load(f)
    with open(summary_accurate, 'r') as f:
        accurate_summary = json.load(f)
    
    assert fast_summary["num_queries"] == accurate_summary["num_queries"], \
        "Fast and accurate lanes processed different numbers of queries"
    
    print(f"✓ Both lanes processed {fast_summary['num_queries']} queries")
    
    return fast_summary["num_queries"]

def main():
    """Run all tests."""
    print("Running evaluation system tests...\n")
    
    try:
        # Test YAML loading and coverage
        total_prompts, stones, fields = test_yaml_loading()
        
        # Test evaluation output
        num_queries = test_eval_output()
        
        # Verify consistency
        assert total_prompts == num_queries, \
            f"YAML loading found {total_prompts} prompts but evaluation processed {num_queries}"
        
        print(f"\n🎉 All tests passed!")
        print(f"✅ {total_prompts} prompts loaded from YAML files")
        print(f"✅ {len(stones)} stones covered (≥3 prompts each)")
        print(f"✅ {len(fields)} fields covered (≥1 prompt each)")
        print(f"✅ Both lanes evaluated successfully")
        print(f"✅ Output files generated correctly")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
