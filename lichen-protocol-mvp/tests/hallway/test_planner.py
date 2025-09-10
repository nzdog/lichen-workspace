"""
Tests for the pure room planning function.
"""

import pytest
from hallway.planner import plan_rooms


class TestPlanner:
    """Test room planning logic."""

    def test_full_sequence_no_subset_no_mini_walk(self):
        """Test full sequence with no subset and no mini-walk."""
        sequence = ["entry", "diagnostic", "protocol", "walk", "memory", "exit"]
        result = plan_rooms(sequence, None, False)
        assert result == sequence

    def test_mini_walk_no_subset(self):
        """Test mini-walk returns first three rooms."""
        sequence = ["entry", "diagnostic", "protocol", "walk", "memory", "exit"]
        result = plan_rooms(sequence, None, True)
        assert result == ["entry", "diagnostic", "protocol"]

    def test_mini_walk_short_sequence(self):
        """Test mini-walk with sequence shorter than 3."""
        sequence = ["entry", "diagnostic"]
        result = plan_rooms(sequence, None, True)
        assert result == ["entry", "diagnostic"]

    def test_subset_preserves_order_no_mini_walk(self):
        """Test subset preserves original order."""
        sequence = ["entry", "diagnostic", "protocol", "walk", "memory", "exit"]
        subset = ["protocol", "entry", "memory"]  # Different order than sequence
        result = plan_rooms(sequence, subset, False)
        # Should preserve sequence order, not subset order
        assert result == ["entry", "protocol", "memory"]

    def test_subset_preserves_order_with_mini_walk(self):
        """Test subset takes precedence over mini-walk."""
        sequence = ["entry", "diagnostic", "protocol", "walk", "memory", "exit"]
        subset = ["walk", "exit"]
        result = plan_rooms(sequence, subset, True)
        # Subset should override mini-walk
        assert result == ["walk", "exit"]

    def test_empty_subset(self):
        """Test empty subset list behaves like None."""
        sequence = ["entry", "diagnostic", "protocol", "walk", "memory", "exit"]
        result = plan_rooms(sequence, [], True)
        assert result == ["entry", "diagnostic", "protocol"]

    def test_subset_not_in_sequence(self):
        """Test subset with items not in sequence."""
        sequence = ["entry", "diagnostic", "protocol"]
        subset = ["entry", "nonexistent", "protocol"]
        result = plan_rooms(sequence, subset, False)
        # Should only include items that exist in sequence
        assert result == ["entry", "protocol"]

    def test_sequence_length_exactly_three_mini_walk(self):
        """Test mini-walk with sequence length exactly 3."""
        sequence = ["entry", "diagnostic", "protocol"]
        result = plan_rooms(sequence, None, True)
        assert result == ["entry", "diagnostic", "protocol"]  # all three

    def test_sequence_length_one_mini_walk(self):
        """Test mini-walk with sequence length 1."""
        sequence = ["entry"]
        result = plan_rooms(sequence, None, True)
        assert result == ["entry"]

    def test_empty_sequence(self):
        """Test empty sequence."""
        result = plan_rooms([], None, False)
        assert result == []

    def test_empty_sequence_mini_walk(self):
        """Test empty sequence with mini-walk."""
        result = plan_rooms([], None, True)
        assert result == []

    def test_sequence_is_copied(self):
        """Test that original sequence is not modified."""
        sequence = ["entry", "diagnostic", "protocol"]
        original = sequence.copy()
        result = plan_rooms(sequence, None, False)

        # Verify original sequence unchanged
        assert sequence == original
        # Verify result is a different list
        assert result is not sequence
