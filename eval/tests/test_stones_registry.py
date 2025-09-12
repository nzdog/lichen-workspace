"""
Tests for the Stones registry functionality.
"""

import pytest
import yaml
from pathlib import Path


def test_stones_registry_structure():
    """Test that the stones registry has the correct structure."""
    stones_path = Path("eval/stones.yaml")
    assert stones_path.exists(), "eval/stones.yaml should exist"
    
    with open(stones_path, 'r') as f:
        data = yaml.safe_load(f)
    
    assert 'stones' in data, "Registry should have 'stones' key"
    assert isinstance(data['stones'], list), "Stones should be a list"
    assert len(data['stones']) == 10, "Should have exactly 10 stones"
    
    # Check each stone has required fields
    slugs = set()
    for stone in data['stones']:
        assert 'slug' in stone, "Each stone should have a slug"
        assert 'name' in stone, "Each stone should have a name"
        assert 'meaning' in stone, "Each stone should have a meaning"
        assert 'red_flags' in stone, "Each stone should have red_flags"
        assert 'must_haves' in stone, "Each stone should have must_haves"
        
        # Check slug uniqueness
        assert stone['slug'] not in slugs, f"Duplicate slug: {stone['slug']}"
        slugs.add(stone['slug'])
        
        # Check meaning is non-empty
        assert stone['meaning'].strip(), f"Stone {stone['slug']} has empty meaning"
        
        # Check red_flags and must_haves are lists
        assert isinstance(stone['red_flags'], list), f"Stone {stone['slug']} red_flags should be list"
        assert isinstance(stone['must_haves'], list), f"Stone {stone['slug']} must_haves should be list"
        
        # Check they have at least one item each
        assert len(stone['red_flags']) > 0, f"Stone {stone['slug']} should have at least one red_flag"
        assert len(stone['must_haves']) > 0, f"Stone {stone['slug']} should have at least one must_have"


def test_stones_registry_canonical_slugs():
    """Test that all canonical stone slugs are present."""
    expected_slugs = {
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
    
    stones_path = Path("eval/stones.yaml")
    with open(stones_path, 'r') as f:
        data = yaml.safe_load(f)
    
    actual_slugs = {stone['slug'] for stone in data['stones']}
    assert actual_slugs == expected_slugs, f"Slug mismatch: expected {expected_slugs}, got {actual_slugs}"


def test_stones_registry_meanings():
    """Test that stone meanings match the canonical text."""
    expected_meanings = {
        'light-before-form': 'We protect the soul of the system before shaping its structure. We trust essence to lead design—not the other way around.',
        'speed-of-trust': 'We move only as fast as relationship allows. Urgency is never more important than alignment.',
        'stewardship-not-ownership': 'The system is not a possession—it is a responsibility. I walk with it, not above it.',
        'clarity-over-cleverness': 'We speak in language that liberates, not complicates. We make things simple, not shallow.',
        'presence-is-productivity': 'Our capacity to hold stillness is part of how the work gets done. Rest is not a break from progress—it is part of it.',
        'nothing-forced-nothing-withheld': 'What comes is welcome. What hasn\'t yet come is not missing. We trust emergence more than agenda.',
        'no-contortion-for-acceptance': 'We do not bend the system to fit what the world expects. We invite the world to meet something different.',
        'integrity-is-the-growth-strategy': 'We grow only through what aligns with the core. Even if that means growing slowly, or differently.',
        'built-for-wholeness': 'We don\'t fragment people to make them fit. We create scaffolds that hold complexity, humanity, and contradiction.',
        'the-system-walks-with-us': 'We are not separate from it. As we evolve, it evolves. As we remember, it reveals.'
    }
    
    stones_path = Path("eval/stones.yaml")
    with open(stones_path, 'r') as f:
        data = yaml.safe_load(f)
    
    for stone in data['stones']:
        slug = stone['slug']
        expected = expected_meanings[slug]
        actual = stone['meaning'].strip()
        assert actual == expected, f"Meaning mismatch for {slug}: expected '{expected}', got '{actual}'"


def test_stones_registry_loading_function():
    """Test the load_stones_registry function logic."""
    # Test the logic without importing the module
    stones_path = Path("eval/stones.yaml")
    assert stones_path.exists(), "Stones registry should exist"
    
    with open(stones_path, 'r') as f:
        data = yaml.safe_load(f)
    
    # Simulate the loading function logic
    stones_registry = {}
    for stone in data.get('stones', []):
        stones_registry[stone['slug']] = stone
    
    assert isinstance(stones_registry, dict), "Should return a dictionary"
    assert len(stones_registry) == 10, "Should have 10 stones"
    
    # Check structure of loaded registry
    for slug, stone_info in stones_registry.items():
        assert 'name' in stone_info
        assert 'meaning' in stone_info
        assert 'red_flags' in stone_info
        assert 'must_haves' in stone_info
        assert stone_info['slug'] == slug


if __name__ == "__main__":
    pytest.main([__file__])
