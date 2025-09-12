"""
Tests for semantic alignment assertion functionality.
"""

import pytest


def check_semantic_alignment(answer: str, stone_info: dict, assertions: list) -> dict:
    """
    Check semantic alignment of answer against Stone meaning and assertions.
    Standalone version for testing.
    """
    result = {
        "passed": True,
        "failed_assertions": [],
        "must_have_matches": [],
        "red_flag_matches": []
    }
    
    answer_lower = answer.lower()
    
    # Check for must_have phrases (positive alignment)
    must_haves = stone_info.get('must_haves', [])
    for must_have in must_haves:
        # Simple keyword matching - could be enhanced with embeddings
        must_have_lower = must_have.lower()
        if any(word in answer_lower for word in must_have_lower.split()):
            result["must_have_matches"].append(must_have)
    
    # Check for red_flag phrases (negative alignment)
    red_flags = stone_info.get('red_flags', [])
    for red_flag in red_flags:
        red_flag_lower = red_flag.lower()
        if any(word in answer_lower for word in red_flag_lower.split()):
            result["red_flag_matches"].append(red_flag)
            result["passed"] = False
    
    # Check if assertions require stone meaning reference
    requires_stone_meaning = any("must_reference_stone_meaning" in assertion for assertion in assertions)
    if requires_stone_meaning:
        # Must have at least one must_have match
        if not result["must_have_matches"]:
            result["failed_assertions"].append("must_reference_stone_meaning")
            result["passed"] = False
    
    return result


def test_semantic_alignment_pass_example():
    """Test semantic alignment with a passing example for speed-of-trust."""
    
    stone_info = {
        'slug': 'speed-of-trust',
        'name': 'The Speed of Trust',
        'meaning': 'We move only as fast as relationship allows. Urgency is never more important than alignment.',
        'red_flags': [
            'urgency overriding alignment',
            'pushing pace without consent'
        ],
        'must_haves': [
            'checks agreement compatibility',
            'makes tradeoffs explicit regarding relationships'
        ]
    }
    
    # Good answer that includes must_have concepts
    good_answer = """
    When building relationships with your team under pressure, it's crucial to check for agreement and fit 
    before moving forward. Make tradeoffs explicit with respect to relationships - explain why certain 
    decisions are being made and how they impact the team. Don't rush the process just 
    because of external deadlines.
    """
    
    assertions = ["Should emphasize trust-building over speed"]
    
    result = check_semantic_alignment(good_answer, stone_info, assertions)
    
    assert result['passed'] is True, f"Should pass but got: {result}"
    assert len(result['must_have_matches']) > 0, "Should have must_have matches"
    assert len(result['red_flag_matches']) == 0, "Should have no red_flag matches"
    assert len(result['failed_assertions']) == 0, "Should have no failed assertions"


def test_semantic_alignment_fail_example():
    """Test semantic alignment with a failing example for speed-of-trust."""
    
    stone_info = {
        'slug': 'speed-of-trust',
        'name': 'The Speed of Trust',
        'meaning': 'We move only as fast as relationship allows. Urgency is never more important than alignment.',
        'red_flags': [
            'urgency overriding alignment',
            'pushing pace without consent'
        ],
        'must_haves': [
            'checks agreement compatibility',
            'makes tradeoffs explicit regarding relationships'
        ]
    }
    
    # Bad answer that includes red_flag concepts but no must_have concepts
    bad_answer = """
    When under pressure, you need to push pace without waiting for full approval from everyone. 
    Urgency should override alignment concerns - just get the work done quickly and worry about 
    team dynamics later. Speed is more important than collaboration in high-pressure situations.
    """
    
    assertions = ["Should emphasize trust-building over speed"]
    
    result = check_semantic_alignment(bad_answer, stone_info, assertions)
    
    assert result['passed'] is False, f"Should fail but got: {result}"
    assert len(result['red_flag_matches']) > 0, "Should have red_flag matches"
    assert len(result['must_have_matches']) == 0, "Should have no must_have matches"


def test_semantic_alignment_must_reference_stone_meaning():
    """Test the must_reference_stone_meaning assertion."""
    
    stone_info = {
        'slug': 'speed-of-trust',
        'name': 'The Speed of Trust',
        'meaning': 'We move only as fast as relationship allows. Urgency is never more important than alignment.',
        'red_flags': [
            'urgency overriding alignment',
            'pushing pace without consent'
        ],
        'must_haves': [
            'checks agreement compatibility',
            'makes tradeoffs explicit regarding relationships'
        ]
    }
    
    # Answer without must_have concepts
    answer_without_must_haves = """
    Team dynamics are important. You should be honest and transparent with your team members.
    """
    
    assertions = ["Should emphasize trust-building over speed", "must_reference_stone_meaning: true"]
    
    result = check_semantic_alignment(answer_without_must_haves, stone_info, assertions)
    
    assert result['passed'] is False, f"Should fail due to missing must_have references"
    assert "must_reference_stone_meaning" in result['failed_assertions'], "Should have failed must_reference_stone_meaning assertion"
    
    # Answer with must_have concepts
    answer_with_must_haves = """
    When building relationships, always check for agreement and fit before proceeding. Make tradeoffs
    explicit with respect to relationships, explaining how decisions impact the team.
    """
    
    result = check_semantic_alignment(answer_with_must_haves, stone_info, assertions)
    
    assert result['passed'] is True, f"Should pass with must_have references"
    assert "must_reference_stone_meaning" not in result['failed_assertions'], "Should not have failed must_reference_stone_meaning assertion"


def test_semantic_alignment_edge_cases():
    """Test edge cases for semantic alignment."""
    
    stone_info = {
        'slug': 'test-stone',
        'name': 'Test Stone',
        'meaning': 'Test meaning',
        'red_flags': [],
        'must_haves': []
    }
    
    # Empty answer
    result = check_semantic_alignment("", stone_info, [])
    assert result['passed'] is True, "Empty answer should pass when no requirements"
    
    # Answer with no assertions
    result = check_semantic_alignment("Some answer", stone_info, [])
    assert result['passed'] is True, "Answer should pass when no assertions"
    
    # Answer with empty assertions
    result = check_semantic_alignment("Some answer", stone_info, [""])
    assert result['passed'] is True, "Answer should pass with empty assertions"


if __name__ == "__main__":
    pytest.main([__file__])
