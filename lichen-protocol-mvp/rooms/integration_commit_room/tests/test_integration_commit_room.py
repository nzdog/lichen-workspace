import pytest
from datetime import datetime
from rooms.integration_commit_room.integration_commit_room import IntegrationCommitRoom, run_integration_commit_room
from rooms.integration_commit_room.contract_types import (
    IntegrationCommitRoomInput, IntegrationCommitRoomOutput, IntegrationData,
    Commitment, PaceState, MemoryWriteResult, DeclineReason, RoomState
)
from rooms.integration_commit_room.integration import IntegrationEnforcement
from rooms.integration_commit_room.commits import CommitRecording
from rooms.integration_commit_room.pace import PaceEnforcement
from rooms.integration_commit_room.memory_write import MemoryWrite
from rooms.integration_commit_room.completion import Completion


class TestIntegrationEnforcement:
    """Test integration enforcement functionality"""
    
    def test_validate_integration_presence_success(self):
        """Test successful integration validation"""
        payload = {
            "integration_notes": "Feeling more grounded after the session",
            "session_context": "Morning meditation practice"
        }
        
        is_valid, integration_data, decline_response = IntegrationEnforcement.validate_integration_presence(payload)
        
        assert is_valid is True
        assert integration_data is not None
        assert decline_response is None
        assert integration_data.integration_notes == "Feeling more grounded after the session"
        assert integration_data.session_context == "Morning meditation practice"
    
    def test_validate_integration_presence_missing_fields(self):
        """Test integration validation with missing fields"""
        payload = {"integration_notes": "Some notes"}
        
        is_valid, integration_data, decline_response = IntegrationEnforcement.validate_integration_presence(payload)
        
        assert is_valid is False
        assert integration_data is None
        assert decline_response is not None
        assert decline_response.reason == DeclineReason.MISSING_INTEGRATION
        assert "session_context" in decline_response.message
    
    def test_validate_integration_presence_empty_payload(self):
        """Test integration validation with empty payload"""
        payload = None
        
        is_valid, integration_data, decline_response = IntegrationEnforcement.validate_integration_presence(payload)
        
        assert is_valid is False
        assert integration_data is None
        assert decline_response is not None
        assert decline_response.reason == DeclineReason.MISSING_INTEGRATION
    
    def test_validate_integration_quality_success(self):
        """Test successful integration quality validation"""
        integration_data = IntegrationData(
            integration_notes="This is a meaningful integration note with sufficient content",
            session_context="Morning session"
        )
        
        is_valid, decline_response = IntegrationEnforcement.validate_integration_quality(integration_data)
        
        assert is_valid is True
        assert decline_response is None
    
    def test_validate_integration_quality_too_short(self):
        """Test integration quality validation with too short content"""
        integration_data = IntegrationData(
            integration_notes="Short",
            session_context="Morning session"
        )
        
        is_valid, decline_response = IntegrationEnforcement.validate_integration_quality(integration_data)
        
        assert is_valid is False
        assert decline_response is not None
        assert "meaningful content" in decline_response.message
    
    def test_validate_integration_quality_placeholder_text(self):
        """Test integration quality validation with placeholder text"""
        integration_data = IntegrationData(
            integration_notes="This is a good note",
            session_context="unspecified"
        )
        
        is_valid, decline_response = IntegrationEnforcement.validate_integration_quality(integration_data)
        
        assert is_valid is False
        assert decline_response is not None
        assert "actual content" in decline_response.message


class TestCommitRecording:
    """Test commitment recording functionality"""
    
    def test_validate_commitment_structure_success(self):
        """Test successful commitment structure validation"""
        payload = {
            "commitments": [
                {
                    "text": "Practice daily meditation",
                    "context": "Morning routine",
                    "pace_state": "NOW",
                    "session_ref": "session-123"
                }
            ]
        }
        
        is_valid, commitments, decline_response = CommitRecording.validate_commitment_structure(payload)
        
        assert is_valid is True
        assert commitments is not None
        assert decline_response is None
        assert len(commitments) == 1
        assert commitments[0].text == "Practice daily meditation"
        assert commitments[0].pace_state == PaceState.NOW
    
    def test_validate_commitment_structure_missing_commitments(self):
        """Test commitment validation with missing commitments field"""
        payload = {"other_field": "value"}
        
        is_valid, commitments, decline_response = CommitRecording.validate_commitment_structure(payload)
        
        assert is_valid is False
        assert commitments is None
        assert decline_response is not None
        assert decline_response.reason == DeclineReason.INVALID_COMMITMENT_STRUCTURE
    
    def test_validate_commitment_structure_empty_list(self):
        """Test commitment validation with empty commitments list"""
        payload = {"commitments": []}
        
        is_valid, commitments, decline_response = CommitRecording.validate_commitment_structure(payload)
        
        assert is_valid is False
        assert commitments is None
        assert decline_response is not None
        assert "one commitment is required" in decline_response.message
    
    def test_validate_commitment_structure_invalid_commitment(self):
        """Test commitment validation with invalid commitment data"""
        payload = {
            "commitments": [
                {
                    "text": "Practice daily meditation",
                    "context": "Morning routine"
                    # Missing pace_state and session_ref
                }
            ]
        }
        
        is_valid, commitments, decline_response = CommitRecording.validate_commitment_structure(payload)
        
        assert is_valid is False
        assert commitments is None
        assert decline_response is not None
        assert "Missing required fields" in decline_response.message
    
    def test_validate_commitment_structure_invalid_pace_state(self):
        """Test commitment validation with invalid pace state"""
        payload = {
            "commitments": [
                {
                    "text": "Practice daily meditation",
                    "context": "Morning routine",
                    "pace_state": "INVALID_PACE",
                    "session_ref": "session-123"
                }
            ]
        }
        
        is_valid, commitments, decline_response = CommitRecording.validate_commitment_structure(payload)
        
        assert is_valid is False
        assert commitments is None
        assert decline_response is not None
        assert "Invalid pace_state" in decline_response.message


class TestPaceEnforcement:
    """Test pace enforcement functionality"""
    
    def test_validate_pace_states_success(self):
        """Test successful pace state validation"""
        commitments = [
            Commitment(
                text="Practice meditation",
                context="Morning routine",
                pace_state=PaceState.NOW,
                session_ref="session-123"
            ),
            Commitment(
                text="Read book",
                context="Evening routine",
                pace_state=PaceState.LATER,
                session_ref="session-123"
            )
        ]
        
        is_valid, decline_response = PaceEnforcement.validate_pace_states(commitments)
        
        assert is_valid is True
        assert decline_response is None
    
    def test_validate_pace_states_missing_pace(self):
        """Test pace validation with missing pace state"""
        commitments = [
            Commitment(
                text="Practice meditation",
                context="Morning routine",
                pace_state=None,  # Missing pace state
                session_ref="session-123"
            )
        ]
        
        is_valid, decline_response = PaceEnforcement.validate_pace_states(commitments)
        
        assert is_valid is False
        assert decline_response is not None
        assert decline_response.reason == DeclineReason.MISSING_PACE_STATE
    
    def test_map_pace_to_action(self):
        """Test pace state to action mapping"""
        assert PaceEnforcement.map_pace_to_action(PaceState.NOW) == "continue"
        assert PaceEnforcement.map_pace_to_action(PaceState.HOLD) == "hold"
        assert PaceEnforcement.map_pace_to_action(PaceState.SOFT_HOLD) == "hold"
        assert PaceEnforcement.map_pace_to_action(PaceState.LATER) == "later"
    
    def test_get_room_next_action(self):
        """Test room next action determination"""
        commitments = [
            Commitment(
                text="Practice meditation",
                context="Morning routine",
                pace_state=PaceState.NOW,
                session_ref="session-123"
            ),
            Commitment(
                text="Read book",
                context="Evening routine",
                pace_state=PaceState.LATER,
                session_ref="session-123"
            )
        ]
        
        next_action = PaceEnforcement.get_room_next_action(commitments)
        
        # LATER has higher priority than NOW, so should return "later"
        assert next_action == "later"
    
    def test_get_pace_distribution(self):
        """Test pace distribution calculation"""
        commitments = [
            Commitment(
                text="Practice meditation",
                context="Morning routine",
                pace_state=PaceState.NOW,
                session_ref="session-123"
            ),
            Commitment(
                text="Read book",
                context="Evening routine",
                pace_state=PaceState.LATER,
                session_ref="session-123"
            ),
            Commitment(
                text="Exercise",
                context="Afternoon routine",
                pace_state=PaceState.NOW,
                session_ref="session-123"
            )
        ]
        
        distribution = PaceEnforcement.get_pace_distribution(commitments)
        
        assert distribution["NOW"] == 2
        assert distribution["LATER"] == 1
        assert distribution["HOLD"] == 0
        assert distribution["SOFT_HOLD"] == 0


class TestMemoryWrite:
    """Test memory write functionality"""
    
    def test_write_integration_and_commitments_success(self):
        """Test successful memory write"""
        memory_write = MemoryWrite()
        
        integration_data = IntegrationData(
            integration_notes="Feeling grounded after session",
            session_context="Morning meditation"
        )
        
        commitments = [
            Commitment(
                text="Practice daily meditation",
                context="Morning routine",
                pace_state=PaceState.NOW,
                session_ref="session-123"
            )
        ]
        
        result = memory_write.write_integration_and_commitments(
            "session-123", integration_data, commitments
        )
        
        assert result.success is True
        assert result.integration_written is True
        assert result.commitments_written == 1
        
        # Verify data was stored
        stored_data = memory_write.read_integration_and_commitments("session-123")
        assert stored_data is not None
        assert stored_data["session_id"] == "session-123"
        assert len(stored_data["commitments"]) == 1
    
    def test_write_integration_and_commitments_failure(self):
        """Test memory write failure handling"""
        memory_write = MemoryWrite()
        
        # Test with invalid inputs
        result = memory_write.write_integration_and_commitments(
            "", None, []  # Invalid inputs
        )
        
        assert result.success is False
        assert "Session ID is required" in result.reason
    
    def test_atomic_write_semantics(self):
        """Test that memory write is atomic (no partial writes)"""
        memory_write = MemoryWrite()
        
        # Clear storage first
        memory_write.clear_memory_storage()
        
        integration_data = IntegrationData(
            integration_notes="Test integration",
            session_context="Test context"
        )
        
        commitments = [
            Commitment(
                text="Test commitment",
                context="Test context",
                pace_state=PaceState.NOW,
                session_ref="session-123"
            )
        ]
        
        # Write data
        result = memory_write.write_integration_and_commitments(
            "session-123", integration_data, commitments
        )
        
        assert result.success is True
        
        # Verify both integration and commitments were written
        stored_data = memory_write.read_integration_and_commitments("session-123")
        assert stored_data is not None
        assert "integration" in stored_data
        assert "commitments" in stored_data
        assert len(stored_data["commitments"]) == 1


class TestCompletion:
    """Test completion functionality"""
    
    def test_append_completion_marker(self):
        """Test completion marker appending"""
        text = "Operation completed"
        result = Completion.append_completion_marker(text)
        
        assert result.endswith(" [[COMPLETE]]")
        assert " [[COMPLETE]]" in result
    
    def test_validate_completion_requirements(self):
        """Test completion requirement validation"""
        room_state = RoomState()
        
        # Initially incomplete
        is_complete, missing = Completion.validate_completion_requirements(room_state)
        assert is_complete is False
        assert len(missing) > 0
        
        # Mark as complete
        room_state.integration_captured = True
        room_state.commitments_recorded = True
        room_state.pace_enforced = True
        room_state.memory_written = True
        room_state.integration_data = IntegrationData(
            integration_notes="Test notes",
            session_context="Test context"
        )
        room_state.commitments = [
            Commitment(
                text="Test commitment",
                context="Test context",
                pace_state=PaceState.NOW,
                session_ref="session-123"
            )
        ]
        
        # Now should be complete
        is_complete, missing = Completion.validate_completion_requirements(room_state)
        assert is_complete is True
        assert len(missing) == 0
    
    def test_get_completion_status(self):
        """Test completion status generation"""
        room_state = RoomState()
        room_state.integration_captured = True
        room_state.commitments_recorded = True
        room_state.pace_enforced = True
        room_state.memory_written = True
        
        status = Completion.get_completion_status(room_state)
        assert "satisfied" in status
    
    def test_can_terminate_room(self):
        """Test room termination check"""
        room_state = RoomState()
        
        # Initially cannot terminate
        assert Completion.can_terminate_room(room_state) is False
        
        # Mark as complete
        room_state.integration_captured = True
        room_state.commitments_recorded = True
        room_state.pace_enforced = True
        room_state.memory_written = True
        room_state.integration_data = IntegrationData(
            integration_notes="Test notes",
            session_context="Test context"
        )
        room_state.commitments = [
            Commitment(
                text="Test commitment",
                context="Test context",
                pace_state=PaceState.NOW,
                session_ref="session-123"
            )
        ]
        
        # Now can terminate
        assert Completion.can_terminate_room(room_state) is True


class TestIntegrationCommitRoom:
    """Test main Integration & Commit Room orchestrator"""
    
    def test_integration_commit_room_initialization(self):
        """Test Integration & Commit Room initialization"""
        room = IntegrationCommitRoom()
        assert room.room_states == {}
        assert room.memory_write is not None
    
    def test_capture_integration_success(self):
        """Test successful integration capture"""
        room = IntegrationCommitRoom()
        input_data = IntegrationCommitRoomInput(
            session_state_ref="session-123",
            payload={
                "integration_notes": "Feeling more grounded and centered after the session",
                "session_context": "Morning meditation practice focusing on breath awareness"
            }
        )
        
        result = room.run_integration_commit_room(input_data)
        
        assert "Integration Captured Successfully" in result.display_text
        assert result.display_text.endswith(" [[COMPLETE]]")
        assert result.next_action == "continue"
        
        # Verify state was updated
        room_state = room.get_room_state("session-123")
        assert room_state.integration_captured is True
        assert room_state.integration_data is not None
    
    def test_capture_integration_missing_fields(self):
        """Test integration capture with missing fields"""
        room = IntegrationCommitRoom()
        input_data = IntegrationCommitRoomInput(
            session_state_ref="session-123",
            payload={"integration_notes": "Some notes"}
        )
        
        result = room.run_integration_commit_room(input_data)
        
        assert "Integration Capture" in result.display_text
        assert "Failed" in result.display_text or "missing required fields" in result.display_text.lower()
        assert result.display_text.endswith(" [[COMPLETE]]")
    
    def test_record_commitments_success(self):
        """Test successful commitment recording"""
        room = IntegrationCommitRoom()
        
        # First capture integration
        integration_input = IntegrationCommitRoomInput(
            session_state_ref="session-123",
            payload={
                "integration_notes": "Feeling grounded after session",
                "session_context": "Morning meditation"
            }
        )
        room.run_integration_commit_room(integration_input)
        
        # Then record commitments
        commitments_input = IntegrationCommitRoomInput(
            session_state_ref="session-123",
            payload={
                "commitments": [
                    {
                        "text": "Practice daily meditation",
                        "context": "Morning routine",
                        "pace_state": "NOW",
                        "session_ref": "session-123"
                    },
                    {
                        "text": "Read mindfulness book",
                        "context": "Evening routine",
                        "pace_state": "LATER",
                        "session_ref": "session-123"
                    }
                ]
            }
        )
        
        result = room.run_integration_commit_room(commitments_input)
        
        assert "Commitments Recorded Successfully" in result.display_text
        assert result.display_text.endswith(" [[COMPLETE]]")
        
        # Verify state was updated
        room_state = room.get_room_state("session-123")
        assert room_state.commitments_recorded is True
        assert room_state.pace_enforced is True
        assert len(room_state.commitments) == 2
    
    def test_record_commitments_without_integration(self):
        """Test commitment recording without integration"""
        room = IntegrationCommitRoom()
        input_data = IntegrationCommitRoomInput(
            session_state_ref="session-123",
            payload={
                "commitments": [
                    {
                        "text": "Practice meditation",
                        "context": "Morning routine",
                        "pace_state": "NOW",
                        "session_ref": "session-123"
                    }
                ]
            }
        )
        
        result = room.run_integration_commit_room(input_data)
        
        assert "Integration must be captured before commitments" in result.display_text
        assert result.display_text.endswith(" [[COMPLETE]]")
    
    def test_room_completion_success(self):
        """Test successful room completion"""
        room = IntegrationCommitRoom()
        
        # Complete the full flow
        integration_input = IntegrationCommitRoomInput(
            session_state_ref="session-123",
            payload={
                "integration_notes": "Feeling grounded after session",
                "session_context": "Morning meditation"
            }
        )
        room.run_integration_commit_room(integration_input)
        
        commitments_input = IntegrationCommitRoomInput(
            session_state_ref="session-123",
            payload={
                "commitments": [
                    {
                        "text": "Practice daily meditation",
                        "context": "Morning routine",
                        "pace_state": "NOW",
                        "session_ref": "session-123"
                    }
                ]
            }
        )
        room.run_integration_commit_room(commitments_input)
        
        # Complete the room
        completion_input = IntegrationCommitRoomInput(
            session_state_ref="session-123",
            payload={"complete": True}
        )
        
        result = room.run_integration_commit_room(completion_input)
        
        assert "Integration & Commit Room - Completion Summary" in result.display_text
        assert result.display_text.endswith(" [[COMPLETE]]")
        assert result.next_action == "continue"  # Based on NOW pace state
        
        # Verify state was updated
        room_state = room.get_room_state("session-123")
        assert room_state.memory_written is True
    
    def test_room_completion_requirements_not_met(self):
        """Test room completion with missing requirements"""
        room = IntegrationCommitRoom()
        
        # Try to complete without integration
        completion_input = IntegrationCommitRoomInput(
            session_state_ref="session-123",
            payload={"complete": True}
        )
        
        result = room.run_integration_commit_room(completion_input)
        
        assert "Cannot complete room - requirements not met" in result.display_text
        assert result.display_text.endswith(" [[COMPLETE]]")
    
    def test_get_room_status(self):
        """Test room status retrieval"""
        room = IntegrationCommitRoom()
        
        # Get initial status
        status_input = IntegrationCommitRoomInput(
            session_state_ref="session-123",
            payload={"status": True}
        )
        
        result = room.run_integration_commit_room(status_input)
        
        assert "Integration & Commit Room Status" in result.display_text
        assert "0.0% complete" in result.display_text
        assert result.display_text.endswith(" [[COMPLETE]]")
    
    def test_default_operation(self):
        """Test default operation when no specific operation is specified"""
        room = IntegrationCommitRoom()
        input_data = IntegrationCommitRoomInput(
            session_state_ref="session-123",
            payload={}
        )
        
        result = room.run_integration_commit_room(input_data)
        
        assert "Integration & Commit Room - Available Operations" in result.display_text
        assert "Available Operations" in result.display_text
        assert result.display_text.endswith(" [[COMPLETE]]")


class TestRunIntegrationCommitRoomFunction:
    """Test standalone run_integration_commit_room function"""
    
    def test_run_integration_commit_room_function(self):
        """Test the standalone function"""
        input_data = IntegrationCommitRoomInput(
            session_state_ref="session-456",
            payload={
                "integration_notes": "Feeling centered and present",
                "session_context": "Evening reflection session"
            }
        )
        
        result = run_integration_commit_room(input_data)
        
        assert isinstance(result, dict)
        assert "Integration Captured Successfully" in result['display_text']
        assert result['display_text'].endswith(" [[COMPLETE]]")
        assert result['next_action'] == "continue"


class TestNoTypeScriptArtifacts:
    """Test that no TypeScript artifacts are present"""
    
    def test_no_typescript_files(self):
        """Test that no .ts files exist in integration_commit_room directory"""
        import os
        integration_commit_room_dir = "rooms/integration_commit_room"
        
        for root, dirs, files in os.walk(integration_commit_room_dir):
            for file in files:
                assert not file.endswith('.ts'), f"TypeScript file found: {file}"
    
    def test_no_typescript_configs(self):
        """Test that no TypeScript config files exist"""
        import os
        integration_commit_room_dir = "rooms/integration_commit_room"
        
        config_files = ['package.json', 'tsconfig.json', 'jest.config.js']
        for config in config_files:
            config_path = os.path.join(integration_commit_room_dir, config)
            assert not os.path.exists(config_path), f"TypeScript config found: {config}"
    
    def test_no_node_modules(self):
        """Test that no node_modules directory exists"""
        import os
        integration_commit_room_dir = "rooms/integration_commit_room"
        node_modules_path = os.path.join(integration_commit_room_dir, "node_modules")
        
        assert not os.path.exists(node_modules_path), "node_modules directory found"


if __name__ == "__main__":
    pytest.main([__file__])
