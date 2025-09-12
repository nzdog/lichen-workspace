"""
Tests for prompt stone_meaning validation.
"""

import pytest
import yaml
import glob
from pathlib import Path


def test_prompt_stone_meanings():
    """Test that all prompts have correct stone_meaning matching the registry."""
    # Load stones registry
    stones_path = Path("eval/stones.yaml")
    with open(stones_path, 'r') as f:
        stones_data = yaml.safe_load(f)
    
    stones_registry = {stone['slug']: stone for stone in stones_data['stones']}
    
    # Load all prompt files
    prompts_dir = Path("eval/prompts")
    yaml_files = glob.glob(str(prompts_dir / "*.yaml"))
    
    assert len(yaml_files) > 0, "Should have at least one prompt file"
    
    mismatches = []
    missing_meanings = []
    unknown_stones = []
    
    for yaml_file in yaml_files:
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        
        if 'prompts' in data:
            for prompt in data['prompts']:
                query_id = prompt.get('query_id', 'unknown')
                
                if 'stone' not in prompt:
                    continue
                
                stone_slug = prompt['stone']
                
                # Check if stone exists in registry
                if stone_slug not in stones_registry:
                    unknown_stones.append(f"{query_id}: unknown stone '{stone_slug}'")
                    continue
                
                # Check if stone_meaning is present
                if 'stone_meaning' not in prompt:
                    missing_meanings.append(f"{query_id}: missing stone_meaning")
                    continue
                
                    # Check if stone_meaning matches registry
                    expected_meaning = stones_registry[stone_slug]['meaning'].strip()
                    actual_meaning = prompt['stone_meaning'].strip()
                    
                    if actual_meaning != expected_meaning:
                        mismatches.append(f"{query_id}: meaning mismatch for stone '{stone_slug}'")
    
    # Report any issues
    if unknown_stones:
        pytest.fail(f"Unknown stones found: {unknown_stones}")
    
    if missing_meanings:
        pytest.fail(f"Missing stone_meaning: {missing_meanings}")
    
    if mismatches:
        pytest.fail(f"Stone meaning mismatches: {mismatches}")


def test_prompt_stone_slugs_canonical():
    """Test that all prompt stone slugs are canonical."""
    canonical_slugs = {
        'light-before-form',
        'speed-of-trust',
        'stewardship-not-ownership',
        'clarity-over-cleverness',
        'presence-is-productivity',
        'nothing-forced-nothing-withheld',
        'no-contortion-for-acceptance',
        'integrity-is-the-growth-strategy',
        'built-for-wholeness',
        'the-system-walks-with-us'
    }
    
    prompts_dir = Path("eval/prompts")
    yaml_files = glob.glob(str(prompts_dir / "*.yaml"))
    
    non_canonical_slugs = set()
    
    for yaml_file in yaml_files:
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        
        if 'prompts' in data:
            for prompt in data['prompts']:
                if 'stone' in prompt:
                    stone_slug = prompt['stone']
                    if stone_slug not in canonical_slugs:
                        non_canonical_slugs.add(stone_slug)
    
    assert len(non_canonical_slugs) == 0, f"Non-canonical stone slugs found: {non_canonical_slugs}"


def test_prompt_structure():
    """Test that all prompts have the required structure."""
    required_fields = ['query_id', 'prompt', 'stone', 'stone_meaning', 'field', 'difficulty', 'assertions']
    
    prompts_dir = Path("eval/prompts")
    yaml_files = glob.glob(str(prompts_dir / "*.yaml"))
    
    missing_fields = []
    
    for yaml_file in yaml_files:
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        
        if 'prompts' in data:
            for prompt in data['prompts']:
                query_id = prompt.get('query_id', 'unknown')
                
                for field in required_fields:
                    if field not in prompt:
                        missing_fields.append(f"{query_id}: missing {field}")
    
    assert len(missing_fields) == 0, f"Missing required fields: {missing_fields}"


if __name__ == "__main__":
    pytest.main([__file__])
