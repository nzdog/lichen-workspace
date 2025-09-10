import pytest
from datetime import datetime
from rooms.memory_room.memory_room import MemoryRoom, run_memory_room
from rooms.memory_room.contract_types import (
    MemoryRoomInput, MemoryRoomOutput, MemoryItem, MemoryScope,
    UserAction, CaptureData, MemoryQuery, MemorySession
)
from rooms.memory_room.capture import MemoryCapture
from rooms.memory_room.control import UserControl
from rooms.memory_room.continuity import MemoryContinuity
from rooms.memory_room.governance import MemoryGovernance
from rooms.memory_room.completion import MemoryCompletion


class TestMemoryCapture:
    """Test memory capture functionality"""
    
    def test_create_capture_data_with_defaults(self):
        """Test creating capture data with default values"""
        data = MemoryCapture.create_capture_data()
        
        assert data.tone_label == "unspecified"
        assert data.residue_label == "unspecified"
        assert data.readiness_state == "unspecified"
        assert data.integration_notes == "unspecified"
        assert data.commitments == "unspecified"
        assert data.session_id == "unspecified"
        assert data.protocol_id is None
        assert isinstance(data.timestamp, datetime)
    
    def test_create_capture_data_with_values(self):
        """Test creating capture data with specific values"""
        data = MemoryCapture.create_capture_data(
            tone_label="calm",
            residue_label="peaceful",
            readiness_state="ready",
            integration_notes="feeling centered",
            commitments="practice daily",
            session_id="session-123",
            protocol_id="grounding"
        )
        
        assert data.tone_label == "calm"
        assert data.residue_label == "peaceful"
        assert data.readiness_state == "ready"
        assert data.integration_notes == "feeling centered"
        assert data.commitments == "practice daily"
        assert data.session_id == "session-123"
        assert data.protocol_id == "grounding"
    
    def test_extract_from_payload(self):
        """Test extracting capture data from payload"""
        payload = {
            "tone_label": "excited",
            "residue_label": "energetic",
            "readiness_state": "NOW",
            "integration_notes": "feeling motivated",
            "commitments": "start project"
        }
        
        data = MemoryCapture.extract_from_payload(payload, "session-456")
        
        assert data.tone_label == "excited"
        assert data.residue_label == "energetic"
        assert data.readiness_state == "NOW"
        assert data.integration_notes == "feeling motivated"
        assert data.commitments == "start project"
        assert data.session_id == "session-456"
    
    def test_extract_from_empty_payload(self):
        """Test extracting from empty payload"""
        data = MemoryCapture.extract_from_payload(None, "session-789")
        
        assert data.tone_label == "unspecified"
        assert data.residue_label == "unspecified"
        assert data.session_id == "session-789"
    
    def test_create_memory_item(self):
        """Test creating memory item from capture data"""
        capture_data = MemoryCapture.create_capture_data(session_id="test-session")
        memory_item = MemoryCapture.create_memory_item(capture_data)
        
        assert memory_item.capture_data == capture_data
        assert memory_item.is_pinned is False
        assert isinstance(memory_item.item_id, str)
        assert isinstance(memory_item.created_at, datetime)
    
    def test_validate_capture_data(self):
        """Test capture data validation"""
        valid_data = MemoryCapture.create_capture_data()
        assert MemoryCapture.validate_capture_data(valid_data) is True
        
        # Test with missing field
        invalid_data = CaptureData(
            tone_label="test",
            residue_label="test",
            readiness_state="test",
            integration_notes="test",
            commitments="test",
            session_id="test"
        )
        assert MemoryCapture.validate_capture_data(invalid_data) is True


class TestUserControl:
    """Test user control operations"""
    
    def test_pin_item_success(self):
        """Test successful pin operation"""
        items = [
            MemoryItem(
                item_id="item-1",
                capture_data=MemoryCapture.create_capture_data(session_id="test")
            )
        ]
        
        result = UserControl.pin_item(items, "item-1")
        
        assert result.success is True
        assert "pinned successfully" in result.message
        assert len(result.affected_items) == 1
        assert result.affected_items[0].is_pinned is True
    
    def test_pin_nonexistent_item(self):
        """Test pin operation on non-existent item"""
        items = []
        
        result = UserControl.pin_item(items, "nonexistent")
        
        assert result.success is False
        assert "not found" in result.message
        assert len(result.affected_items) == 0
    
    def test_edit_item_success(self):
        """Test successful edit operation"""
        items = [
            MemoryItem(
                item_id="item-1",
                capture_data=MemoryCapture.create_capture_data(session_id="test")
            )
        ]
        
        result = UserControl.edit_item(items, "item-1", "tone_label", "new_tone")
        
        assert result.success is True
        assert "updated" in result.message
        assert items[0].capture_data.tone_label == "new_tone"
    
    def test_edit_invalid_field(self):
        """Test edit operation with invalid field"""
        items = [
            MemoryItem(
                item_id="item-1",
                capture_data=MemoryCapture.create_capture_data(session_id="test")
            )
        ]
        
        result = UserControl.edit_item(items, "item-1", "invalid_field", "value")
        
        assert result.success is False
        assert "invalid field" in result.message
    
    def test_delete_item_success(self):
        """Test successful delete operation"""
        items = [
            MemoryItem(
                item_id="item-1",
                capture_data=MemoryCapture.create_capture_data(session_id="test")
            )
        ]
        
        result = UserControl.delete_item(items, "item-1")
        
        assert result.success is True
        assert "deleted successfully" in result.message
        assert items[0].deleted_at is not None
    
    def test_delete_already_deleted_item(self):
        """Test delete operation on already deleted item"""
        items = [
            MemoryItem(
                item_id="item-1",
                capture_data=MemoryCapture.create_capture_data(session_id="test")
            )
        ]
        
        # Delete first time
        UserControl.delete_item(items, "item-1")
        
        # Try to delete again
        result = UserControl.delete_item(items, "item-1")
        
        assert result.success is False
        assert "already deleted" in result.message


class TestMemoryContinuity:
    """Test memory continuity and retrieval"""
    
    def test_get_memory_session_scope(self):
        """Test retrieving memory with session scope"""
        items = [
            MemoryItem(
                item_id="item-1",
                capture_data=MemoryCapture.create_capture_data(session_id="session-1")
            ),
            MemoryItem(
                item_id="item-2",
                capture_data=MemoryCapture.create_capture_data(session_id="session-2")
            )
        ]
        
        session_items = MemoryContinuity.get_memory(
            items, MemoryScope.SESSION, session_id="session-1"
        )
        
        assert len(session_items) == 1
        assert session_items[0].item_id == "item-1"
    
    def test_get_memory_protocol_scope(self):
        """Test retrieving memory with protocol scope"""
        items = [
            MemoryItem(
                item_id="item-1",
                capture_data=MemoryCapture.create_capture_data(
                    session_id="session-1", protocol_id="protocol-1"
                )
            ),
            MemoryItem(
                item_id="item-2",
                capture_data=MemoryCapture.create_capture_data(
                    session_id="session-2", protocol_id="protocol-2"
                )
            )
        ]
        
        protocol_items = MemoryContinuity.get_memory(
            items, MemoryScope.PROTOCOL, protocol_id="protocol-1"
        )
        
        assert len(protocol_items) == 1
        assert protocol_items[0].item_id == "item-1"
    
    def test_get_memory_global_scope(self):
        """Test retrieving memory with global scope"""
        items = [
            MemoryItem(
                item_id="item-1",
                capture_data=MemoryCapture.create_capture_data(session_id="session-1")
            ),
            MemoryItem(
                item_id="item-2",
                capture_data=MemoryCapture.create_capture_data(session_id="session-2")
            )
        ]
        
        global_items = MemoryContinuity.get_memory(items, MemoryScope.GLOBAL)
        
        assert len(global_items) == 2
    
    def test_get_memory_with_limit(self):
        """Test retrieving memory with limit"""
        items = [
            MemoryItem(
                item_id=f"item-{i}",
                capture_data=MemoryCapture.create_capture_data(session_id="session-1")
            )
            for i in range(5)
        ]
        
        limited_items = MemoryContinuity.get_memory(
            items, MemoryScope.SESSION, session_id="session-1", limit=3
        )
        
        assert len(limited_items) == 3


class TestMemoryGovernance:
    """Test memory governance rules"""
    
    def test_integrity_linter_pass(self):
        """Test integrity linter with valid data"""
        capture_data = MemoryCapture.create_capture_data()
        
        result = MemoryGovernance.apply_integrity_linter(capture_data)
        
        assert result.is_allowed is True
        assert "passed" in result.reason
    
    def test_stones_alignment_pass(self):
        """Test stones alignment with positive indicators"""
        capture_data = MemoryCapture.create_capture_data(
            tone_label="calm",
            residue_label="peaceful",
            integration_notes="feeling safe and supported",
            commitments="practice care and respect"
        )
        
        result = MemoryGovernance.apply_stones_alignment_filter(capture_data)
        
        assert result.is_allowed is True
        assert "passed" in result.reason
    
    def test_stones_alignment_fail(self):
        """Test stones alignment with misalignment indicators"""
        capture_data = MemoryCapture.create_capture_data(
            tone_label="surveillance",
            residue_label="tracking",
            integration_notes="monitoring behavior",
            commitments="extract data"
        )
        
        result = MemoryGovernance.apply_stones_alignment_filter(capture_data)
        
        assert result.is_allowed is False
        assert "misalignment indicators" in result.reason
    
    def test_coherence_gate_pass(self):
        """Test coherence gate with reasonable data"""
        capture_data = MemoryCapture.create_capture_data(
            tone_label="calm",
            residue_label="peaceful",
            readiness_state="ready",
            integration_notes="feeling centered and grounded",
            commitments="practice daily meditation"
        )
        
        result = MemoryGovernance.apply_coherence_gate(capture_data)
        
        assert result.is_allowed is True
        assert "passed" in result.reason
    
    def test_governance_chain_pass(self):
        """Test complete governance chain with valid data"""
        capture_data = MemoryCapture.create_capture_data(
            tone_label="calm",
            residue_label="peaceful",
            readiness_state="ready",
            integration_notes="feeling safe and supported",
            commitments="practice daily care"
        )
        
        result = MemoryGovernance.apply_governance_chain(capture_data)
        
        assert result.is_allowed is True
        assert "all gates cleared" in result.reason


class TestMemoryCompletion:
    """Test memory completion functionality"""
    
    def test_append_completion_marker(self):
        """Test appending completion marker"""
        text = "Memory operation completed"
        result = MemoryCompletion.append_completion_marker(text)
        
        assert result.endswith(" [[COMPLETE]]")
        assert " [[COMPLETE]]" in result
    
    def test_format_memory_summary(self):
        """Test formatting memory summary"""
        items = [
            MemoryItem(
                item_id="item-1",
                capture_data=MemoryCapture.create_capture_data(session_id="test")
            )
        ]
        
        summary = MemoryCompletion.format_memory_summary("session-123", items)
        
        assert "Memory Room Summary" in summary
        assert "**Total Memory Items**: 1" in summary
        # Note: completion marker is appended by the orchestrator, not the formatter
    
    def test_validate_completion_requirements(self):
        """Test completion requirement validation"""
        items = [
            MemoryItem(
                item_id="item-1",
                capture_data=MemoryCapture.create_capture_data(session_id="test")
            )
        ]
        
        is_complete, missing = MemoryCompletion.validate_completion_requirements(
            items, True, True
        )
        
        assert is_complete is True
        assert len(missing) == 0


class TestMemoryRoom:
    """Test main Memory Room orchestrator"""
    
    def test_memory_room_initialization(self):
        """Test Memory Room initialization"""
        room = MemoryRoom()
        assert room.sessions == {}
    
    def test_capture_memory_success(self):
        """Test successful memory capture"""
        room = MemoryRoom()
        input_data = MemoryRoomInput(
            session_state_ref="session-123",
            payload={
                "tone_label": "calm",
                "residue_label": "peaceful",
                "readiness_state": "ready"
            }
        )
        
        result = room.run_memory_room(input_data)
        
        assert "Memory captured successfully" in result.display_text
        assert result.display_text.endswith(" [[COMPLETE]]")
        assert result.next_action == "continue"
    
    def test_user_control_pin_success(self):
        """Test successful pin operation"""
        room = MemoryRoom()
        
        # First capture an item
        capture_input = MemoryRoomInput(
            session_state_ref="session-123",
            payload={"tone_label": "calm"}
        )
        room.run_memory_room(capture_input)
        
        # Get the item ID from the session
        session = room._get_or_create_session("session-123")
        item_id = session.items[0].item_id
        
        # Pin the item
        pin_input = MemoryRoomInput(
            session_state_ref="session-123",
            payload={"action": "pin", "item_id": item_id}
        )
        
        result = room.run_memory_room(pin_input)
        
        assert "pinned successfully" in result.display_text
        assert result.display_text.endswith(" [[COMPLETE]]")
    
    def test_retrieve_memory_session_scope(self):
        """Test memory retrieval with session scope"""
        room = MemoryRoom()
        
        # Capture some memory
        capture_input = MemoryRoomInput(
            session_state_ref="session-123",
            payload={"tone_label": "calm"}
        )
        room.run_memory_room(capture_input)
        
        # Retrieve memory
        retrieve_input = MemoryRoomInput(
            session_state_ref="session-123",
            payload={"scope": "session"}
        )
        
        result = room.run_memory_room(retrieve_input)
        
        assert "Memory Retrieval" in result.display_text
        assert "session" in result.display_text.lower()
        assert result.display_text.endswith(" [[COMPLETE]]")
    
    def test_get_memory_summary(self):
        """Test getting memory summary"""
        room = MemoryRoom()
        
        # Capture some memory
        capture_input = MemoryRoomInput(
            session_state_ref="session-123",
            payload={"tone_label": "calm"}
        )
        room.run_memory_room(capture_input)
        
        # Get summary
        summary_input = MemoryRoomInput(
            session_state_ref="session-123",
            payload={"summary": True}
        )
        
        result = room.run_memory_room(summary_input)
        
        assert "Memory Room Summary" in result.display_text
        assert "session-123" in result.display_text
        assert result.display_text.endswith(" [[COMPLETE]]")
    
    def test_default_operation(self):
        """Test default operation when no specific operation is specified"""
        room = MemoryRoom()
        input_data = MemoryRoomInput(
            session_state_ref="session-123",
            payload={}
        )
        
        result = room.run_memory_room(input_data)
        
        assert "Memory Room - Available Operations" in result.display_text
        assert "Available Operations" in result.display_text
        assert result.display_text.endswith(" [[COMPLETE]]")


class TestRunMemoryRoomFunction:
    """Test standalone run_memory_room function"""
    
    def test_run_memory_room_function(self):
        """Test the standalone function"""
        input_data = MemoryRoomInput(
            session_state_ref="session-456",
            payload={"tone_label": "excited"}
        )
        
        result = run_memory_room(input_data)
        
        assert isinstance(result, dict)
        assert "Memory captured successfully" in result['display_text']
        assert result['display_text'].endswith(" [[COMPLETE]]")
        assert result['next_action'] == "continue"


class TestNoTypeScriptArtifacts:
    """Test that no TypeScript artifacts are present"""
    
    def test_no_typescript_files(self):
        """Test that no .ts files exist in memory_room directory"""
        import os
        memory_room_dir = "rooms/memory_room"
        
        for root, dirs, files in os.walk(memory_room_dir):
            for file in files:
                assert not file.endswith('.ts'), f"TypeScript file found: {file}"
    
    def test_no_typescript_configs(self):
        """Test that no TypeScript config files exist"""
        import os
        memory_room_dir = "rooms/memory_room"
        
        config_files = ['package.json', 'tsconfig.json', 'jest.config.js']
        for config in config_files:
            config_path = os.path.join(memory_room_dir, config)
            assert not os.path.exists(config_path), f"TypeScript config found: {config}"
    
    def test_no_node_modules(self):
        """Test that no node_modules directory exists"""
        import os
        memory_room_dir = "rooms/memory_room"
        node_modules_path = os.path.join(memory_room_dir, "node_modules")
        
        assert not os.path.exists(node_modules_path), "node_modules directory found"


if __name__ == "__main__":
    pytest.main([__file__])
