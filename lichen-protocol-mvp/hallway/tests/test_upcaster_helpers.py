"""
Tests for the upcaster helper functions
"""

import pytest
from ..upcaster import map_room_output_to_v02, is_room_decline


class TestUpcasterHelpers:
    """Test the upcaster helper functions"""
    
    def test_map_room_output_to_v02_basic(self):
        """Test basic room output mapping"""
        room_output = {
            "display_text": "Hello world",
            "next_action": "continue"
        }
        
        mapped = map_room_output_to_v02(room_output)
        
        assert mapped["text"] == "Hello world"
        assert mapped["next_action"] == "continue"
    
    def test_map_room_output_to_v02_with_decline(self):
        """Test mapping room output with decline information"""
        room_output = {
            "display_text": "Access denied",
            "next_action": "hold",
            "_decline_reason": "permission_denied",
            "_error_details": {"user_id": "123"}
        }
        
        mapped = map_room_output_to_v02(room_output)
        
        assert mapped["text"] == "Access denied"
        assert mapped["next_action"] == "hold"
        assert mapped["decline"]["reason"] == "permission_denied"
        assert mapped["decline"]["ok"] is False
        assert mapped["decline"]["details"] == {"user_id": "123"}
    
    def test_map_room_output_to_v02_extra_fields(self):
        """Test that extra fields are preserved"""
        room_output = {
            "display_text": "Hello world",
            "next_action": "continue",
            "custom_field": "custom_value",
            "metadata": {"timestamp": "2024-01-01"}
        }
        
        mapped = map_room_output_to_v02(room_output)
        
        assert mapped["text"] == "Hello world"
        assert mapped["next_action"] == "continue"
        assert mapped["custom_field"] == "custom_value"
        assert mapped["metadata"] == {"timestamp": "2024-01-01"}
    
    def test_map_room_output_to_v02_no_display_text(self):
        """Test mapping when display_text is not present"""
        room_output = {
            "next_action": "continue",
            "message": "No display text"
        }
        
        mapped = map_room_output_to_v02(room_output)
        
        assert "text" not in mapped
        assert mapped["next_action"] == "continue"
        assert mapped["message"] == "No display text"
    
    def test_is_room_decline_true_with_reason(self):
        """Test is_room_decline returns True when _decline_reason is present"""
        room_output = {
            "display_text": "Error occurred",
            "_decline_reason": "validation_failed"
        }
        
        assert is_room_decline(room_output) is True
    
    def test_is_room_decline_true_with_hold_action(self):
        """Test is_room_decline returns True when next_action is 'hold'"""
        room_output = {
            "display_text": "Please wait",
            "next_action": "hold"
        }
        
        assert is_room_decline(room_output) is True
    
    def test_is_room_decline_true_with_later_action(self):
        """Test is_room_decline returns True when next_action is 'later'"""
        room_output = {
            "display_text": "Try again later",
            "next_action": "later"
        }
        
        assert is_room_decline(room_output) is True
    
    def test_is_room_decline_false_with_continue(self):
        """Test is_room_decline returns False when next_action is 'continue'"""
        room_output = {
            "display_text": "Proceeding",
            "next_action": "continue"
        }
        
        assert is_room_decline(room_output) is False
    
    def test_is_room_decline_false_no_indicators(self):
        """Test is_room_decline returns False when no decline indicators are present"""
        room_output = {
            "display_text": "Normal output",
            "status": "ok"
        }
        
        assert is_room_decline(room_output) is False
    
    def test_map_room_output_to_v02_empty_input(self):
        """Test mapping with empty room output"""
        room_output = {}
        
        mapped = map_room_output_to_v02(room_output)
        
        assert mapped == {}
    
    def test_map_room_output_to_v02_none_values(self):
        """Test mapping with None values"""
        room_output = {
            "display_text": None,
            "next_action": None,
            "custom_field": None
        }
        
        mapped = map_room_output_to_v02(room_output)
        
        assert mapped["text"] is None
        assert mapped["next_action"] is None
        assert mapped["custom_field"] is None
