"""
Test schema validation for hallway outputs
Verifies that outputs validate against the Hallway v0.2 JSON Schema
"""

import json
import os
import pytest
from jsonschema import validate, ValidationError
from hallway.upcaster import upcast_v01_to_v02


class TestSchemaValidation:
    """Test that hallway outputs validate against the v0.2 schema"""
    
    @classmethod
    def setup_class(cls):
        """Load the v0.2 schema for testing"""
        schema_path = os.path.join(os.path.dirname(__file__), "..", "schemas", "hallway_v0_2.schema.json")
        with open(schema_path, 'r') as f:
            cls.schema = json.load(f)
    
    def test_valid_step_result_from_upcaster(self):
        """Test that upcaster output validates against the schema"""
        step_result = upcast_v01_to_v02(
            room_id="entry_room",
            room_output_v01={
                "display_text": "Hello, world!",
                "next_action": "continue"
            },
            status="ok",
            gate_decisions=[{"gate": "coherence_gate", "allow": True, "reason": "Passed"}]
        )
        
        # Should not raise ValidationError when validating as part of a hallway output
        # Create a minimal hallway output to test
        hallway_output = {
            "room_id": "hallway",
            "title": "Hallway",
            "version": "0.2.0",
            "purpose": "Deterministic multi-room session orchestrator",
            "stone_alignment": ["deterministic", "atomic", "auditable"],
            "sequence": ["entry_room"],
            "mini_walk_supported": True,
            "gate_profile": {
                "chain": ["coherence_gate"],
                "overrides": {}
            },
            "inputs": {
                "session_state_ref": "test-session-123",
                "payloads": {},
                "options": {}
            },
            "outputs": {
                "contract_version": "0.2.0",
                "steps": [step_result],
                "final_state_ref": "test-session-123",
                "exit_summary": {
                    "completed": True,
                    "decline": None,
                    "auditable_hash_chain": [step_result["audit"]["step_hash"]]
                }
            }
        }
        
        # Should not raise ValidationError
        validate(instance=hallway_output, schema=self.schema)
    
    def test_valid_exit_summary_in_context(self):
        """Test that a valid ExitSummary validates in the context of a hallway output"""
        exit_summary = {
            "completed": True,
            "decline": None,
            "auditable_hash_chain": [
                "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
            ]
        }
        
        # Create a minimal hallway output to test
        hallway_output = {
            "room_id": "hallway",
            "title": "Hallway",
            "version": "0.2.0",
            "purpose": "Deterministic multi-room session orchestrator",
            "stone_alignment": ["deterministic", "atomic", "auditable"],
            "sequence": ["entry_room"],
            "mini_walk_supported": True,
            "gate_profile": {
                "chain": ["coherence_gate"],
                "overrides": {}
            },
            "inputs": {
                "session_state_ref": "test-session-123",
                "payloads": {},
                "options": {}
            },
            "outputs": {
                "contract_version": "0.2.0",
                "steps": [],
                "final_state_ref": "test-session-123",
                "exit_summary": exit_summary
            }
        }
        
        # Should not raise ValidationError
        validate(instance=hallway_output, schema=self.schema)
    
    def test_valid_hallway_output(self):
        """Test that a complete hallway output validates against the schema"""
        # Create a minimal valid hallway output
        step_result = upcast_v01_to_v02(
            room_id="entry_room",
            room_output_v01={"display_text": "Hello", "next_action": "continue"},
            status="ok",
            gate_decisions=[{"gate": "coherence_gate", "allow": True, "reason": "Passed"}]
        )
        
        hallway_output = {
            "room_id": "hallway",
            "title": "Hallway",
            "version": "0.2.0",
            "purpose": "Deterministic multi-room session orchestrator",
            "stone_alignment": ["deterministic", "atomic", "auditable"],
            "sequence": ["entry_room", "exit_room"],
            "mini_walk_supported": True,
            "gate_profile": {
                "chain": ["coherence_gate"],
                "overrides": {}
            },
            "inputs": {
                "session_state_ref": "test-session-123",
                "payloads": {},
                "options": {}
            },
            "outputs": {
                "contract_version": "0.2.0",
                "steps": [step_result],
                "final_state_ref": "test-session-123",
                "exit_summary": {
                    "completed": True,
                    "decline": None,
                    "auditable_hash_chain": [step_result["audit"]["step_hash"]]
                }
            }
        }
        
        # Should not raise ValidationError
        validate(instance=hallway_output, schema=self.schema)
    
    def test_invalid_hallway_output_missing_required_fields(self):
        """Test that hallway output with missing required fields fails validation"""
        invalid_hallway_output = {
            "room_id": "hallway",
            "title": "Hallway",
            # Missing version, purpose, stone_alignment, sequence, mini_walk_supported, gate_profile, inputs, outputs
        }
        
        with pytest.raises(ValidationError):
            validate(instance=invalid_hallway_output, schema=self.schema)
    
    def test_invalid_hallway_output_wrong_contract_version(self):
        """Test that hallway output with wrong contract version fails validation"""
        invalid_hallway_output = {
            "room_id": "hallway",
            "title": "Hallway",
            "version": "0.1.0",  # Wrong version
            "purpose": "Deterministic multi-room session orchestrator",
            "stone_alignment": ["deterministic", "atomic", "auditable"],
            "sequence": ["entry_room"],
            "mini_walk_supported": True,
            "gate_profile": {
                "chain": ["coherence_gate"],
                "overrides": {}
            },
            "inputs": {
                "session_state_ref": "test-session-123",
                "payloads": {},
                "options": {}
            },
            "outputs": {
                "contract_version": "0.1.0",  # Wrong version
                "steps": [],
                "final_state_ref": "test-session-123",
                "exit_summary": {
                    "completed": True,
                    "decline": None,
                    "auditable_hash_chain": []
                }
            }
        }
        
        with pytest.raises(ValidationError):
            validate(instance=invalid_hallway_output, schema=self.schema)
    
    def test_invalid_hallway_output_wrong_room_id(self):
        """Test that hallway output with wrong room_id fails validation"""
        invalid_hallway_output = {
            "room_id": "wrong_room",  # Wrong room_id
            "title": "Hallway",
            "version": "0.2.0",
            "purpose": "Deterministic multi-room session orchestrator",
            "stone_alignment": ["deterministic", "atomic", "auditable"],
            "sequence": ["entry_room"],
            "mini_walk_supported": True,
            "gate_profile": {
                "chain": ["coherence_gate"],
                "overrides": {}
            },
            "inputs": {
                "session_state_ref": "test-session-123",
                "payloads": {},
                "options": {}
            },
            "outputs": {
                "contract_version": "0.2.0",
                "steps": [],
                "final_state_ref": "test-session-123",
                "exit_summary": {
                    "completed": True,
                    "decline": None,
                    "auditable_hash_chain": []
                }
            }
        }
        
        with pytest.raises(ValidationError):
            validate(instance=invalid_hallway_output, schema=self.schema)
    
    def test_invalid_hex_hash_format_in_context(self):
        """Test that invalid hex hash format fails validation in hallway context"""
        # Create a step result with invalid hash
        step_result = upcast_v01_to_v02(
            room_id="entry_room",
            room_output_v01={"display_text": "Hello", "next_action": "continue"},
            status="ok",
            gate_decisions=[{"gate": "coherence_gate", "allow": True, "reason": "Passed"}]
        )
        
        # Manually corrupt the hash
        step_result["audit"]["step_hash"] = "invalid_hash"
        
        hallway_output = {
            "room_id": "hallway",
            "title": "Hallway",
            "version": "0.2.0",
            "purpose": "Deterministic multi-room session orchestrator",
            "stone_alignment": ["deterministic", "atomic", "auditable"],
            "sequence": ["entry_room"],
            "mini_walk_supported": True,
            "gate_profile": {
                "chain": ["coherence_gate"],
                "overrides": {}
            },
            "inputs": {
                "session_state_ref": "test-session-123",
                "payloads": {},
                "options": {}
            },
            "outputs": {
                "contract_version": "0.2.0",
                "steps": [step_result],
                "final_state_ref": "test-session-123",
                "exit_summary": {
                    "completed": True,
                    "decline": None,
                    "auditable_hash_chain": ["invalid_hash"]
                }
            }
        }
        
        with pytest.raises(ValidationError):
            validate(instance=hallway_output, schema=self.schema)
    
    def test_valid_hex_hash_formats_in_context(self):
        """Test that valid hex hash formats pass validation in hallway context"""
        valid_hashes = [
            "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        ]
        
        for hash_value in valid_hashes:
            # Create a step result with valid hash
            step_result = upcast_v01_to_v02(
                room_id="entry_room",
                room_output_v01={"display_text": "Hello", "next_action": "continue"},
                status="ok",
                gate_decisions=[{"gate": "coherence_gate", "allow": True, "reason": "Passed"}]
            )
            
            # Manually set the hash
            step_result["audit"]["step_hash"] = hash_value
            
            hallway_output = {
                "room_id": "hallway",
                "title": "Hallway",
                "version": "0.2.0",
                "purpose": "Deterministic multi-room session orchestrator",
                "stone_alignment": ["deterministic", "atomic", "auditable"],
                "sequence": ["entry_room"],
                "mini_walk_supported": True,
                "gate_profile": {
                    "chain": ["coherence_gate"],
                    "overrides": {}
                },
                "inputs": {
                    "session_state_ref": "test-session-123",
                    "payloads": {},
                    "options": {}
                },
                "outputs": {
                    "contract_version": "0.2.0",
                    "steps": [step_result],
                    "final_state_ref": "test-session-123",
                    "exit_summary": {
                        "completed": True,
                        "decline": None,
                        "auditable_hash_chain": [hash_value]
                    }
                }
            }
            
            # Should not raise ValidationError
            validate(instance=hallway_output, schema=self.schema)


if __name__ == "__main__":
    pytest.main([__file__])

