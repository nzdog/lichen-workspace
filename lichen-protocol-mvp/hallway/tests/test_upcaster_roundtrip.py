"""
Test upcaster roundtrip functionality
Verifies that upcast → downcast returns original v0.1 payload
"""

import pytest
from hallway.upcaster import upcast_v01_to_v02, downcast_v02_to_v01, verify_roundtrip


class TestUpcasterRoundtrip:
    """Test upcaster roundtrip functionality"""
    
    def test_simple_roundtrip(self):
        """Test roundtrip with simple room output"""
        original_output = {
            "display_text": "Hello, world!",
            "next_action": "continue",
            "session_id": "test-123"
        }
        
        # Upcast to v0.2
        step_result = upcast_v01_to_v02(
            room_id="entry_room",
            room_output_v01=original_output,
            status="ok",
            gate_decisions=[{"gate": "coherence_gate", "allow": True, "reason": "Passed"}]
        )
        
        # Downcast back to v0.1
        extracted_output = downcast_v02_to_v01(step_result)
        
        # Should be equal
        assert extracted_output == original_output
    
    def test_complex_roundtrip(self):
        """Test roundtrip with complex nested room output"""
        original_output = {
            "display_text": "Complex output",
            "metadata": {
                "timestamp": "2024-01-01T00:00:00Z",
                "version": "1.0.0",
                "nested": {
                    "deep": "value",
                    "array": [1, 2, 3, {"key": "value"}]
                }
            },
            "actions": ["action1", "action2"],
            "flags": {"flag1": True, "flag2": False}
        }
        
        # Upcast to v0.2
        step_result = upcast_v01_to_v02(
            room_id="protocol_room",
            room_output_v01=original_output,
            status="ok",
            gate_decisions=[{"gate": "coherence_gate", "allow": True, "reason": "Passed"}]
        )
        
        # Downcast back to v0.1
        extracted_output = downcast_v02_to_v01(step_result)
        
        # Should be equal
        assert extracted_output == original_output
    
    def test_verify_roundtrip_function(self):
        """Test the verify_roundtrip helper function"""
        original_output = {
            "message": "Test message",
            "data": {"key": "value"}
        }
        
        # Upcast to v0.2
        step_result = upcast_v01_to_v02(
            room_id="diagnostic_room",
            room_output_v01=original_output,
            status="ok",
            gate_decisions=[{"gate": "coherence_gate", "allow": True, "reason": "Passed"}]
        )
        
        # Verify roundtrip
        assert verify_roundtrip(original_output, step_result) is True
    
    def test_roundtrip_with_decline(self):
        """Test roundtrip with room decline output"""
        original_output = {
            "error": "Room declined to proceed",
            "reason": "Invalid input",
            "next_action": "hold"
        }
        
        # Upcast to v0.2 with decline status
        step_result = upcast_v01_to_v02(
            room_id="walk_room",
            room_output_v01=original_output,
            status="decline",
            gate_decisions=[{"gate": "coherence_gate", "allow": False, "reason": "Failed validation"}]
        )
        
        # Downcast back to v0.1
        extracted_output = downcast_v02_to_v01(step_result)
        
        # Should be equal
        assert extracted_output == original_output
    
    def test_roundtrip_preserves_structure(self):
        """Test that roundtrip preserves exact structure including types"""
        original_output = {
            "string": "text",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "null_value": None,
            "list": [1, "two", 3.0],
            "dict": {"nested": "value"}
        }
        
        # Upcast to v0.2
        step_result = upcast_v01_to_v02(
            room_id="memory_room",
            room_output_v01=original_output,
            status="ok",
            gate_decisions=[{"gate": "coherence_gate", "allow": True, "reason": "Passed"}]
        )
        
        # Downcast back to v0.1
        extracted_output = downcast_v02_to_v01(step_result)
        
        # Should be exactly equal
        assert extracted_output == original_output
        
        # Verify types are preserved
        assert isinstance(extracted_output["string"], str)
        assert isinstance(extracted_output["integer"], int)
        assert isinstance(extracted_output["float"], float)
        assert isinstance(extracted_output["boolean"], bool)
        assert extracted_output["null_value"] is None
        assert isinstance(extracted_output["list"], list)
        assert isinstance(extracted_output["dict"], dict)


if __name__ == "__main__":
    pytest.main([__file__])
