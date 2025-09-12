"""
Protocol Room Unit Tests
Tests all behavioral invariants and edge cases using pytest
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rooms.protocol_room.protocol_room import ProtocolRoom, run_protocol_room
from rooms.protocol_room.room_types import ProtocolRoomInput, ProtocolRoomOutput, ProtocolDepth, ProtocolText, ScenarioMapping, IntegrityResult
from rooms.protocol_room.canon import fetch_protocol_text, get_protocol_by_depth, list_available_protocols
from rooms.protocol_room.depth import select_protocol_depth, format_depth_label, get_depth_description
from rooms.protocol_room.mapping import map_scenario_to_protocol, get_scenario_mapping, list_scenario_mappings
from rooms.protocol_room.integrity import check_stones_alignment, check_coherence, run_integrity_gate, validate_protocol_delivery
from rooms.protocol_room.completion import append_fixed_marker


class TestProtocolRoom:
    """Test suite for Protocol Room implementation"""
    
    @pytest.fixture
    def sample_input(self):
        """Sample input for testing"""
        return ProtocolRoomInput(
            session_state_ref='test-session-123',
            payload={
                'protocol_id': 'clearing_entry',
                'depth': 'theme'
            }
        )
    
    @pytest.fixture
    def protocol_room(self):
        """Protocol Room instance for testing"""
        return ProtocolRoom()
    
    def test_canon_fidelity_exact_text_delivery(self):
        """Test that protocol text is delivered exactly as authored, no edits"""
        # Fetch protocol text
        protocol = fetch_protocol_text('clearing_entry')
        assert protocol is not None
        
        # Get text at different depths
        full_text = get_protocol_by_depth('clearing_entry', 'full')
        theme_text = get_protocol_by_depth('clearing_entry', 'theme')
        scenario_text = get_protocol_by_depth('clearing_entry', 'scenario')
        
        # Verify text is not empty
        assert full_text is not None
        assert theme_text is not None
        assert scenario_text is not None
        
        # Verify text contains expected content (exact match)
        assert "Clearing Entry" in full_text
        assert "Mental Decluttering" in full_text
        assert "Clear mental clutter" in theme_text
        assert "13 minutes" in scenario_text
        
        # Verify no text modification occurred
        assert full_text == protocol.full_text
        assert theme_text == protocol.theme_text
        assert scenario_text == protocol.scenario_text
    
    def test_canon_fidelity_no_edits_or_paraphrasing(self):
        """Test that no editing or paraphrasing occurs"""
        # Get original protocol
        original_protocol = fetch_protocol_text('resourcing_mini_walk')
        assert original_protocol is not None
        
        # Get delivered text
        delivered_text = get_protocol_by_depth('resourcing_mini_walk', 'full')
        assert delivered_text is not None
        
        # Verify exact match - no changes
        assert delivered_text == original_protocol.full_text
        
        # Verify specific content is preserved exactly
        assert "Grounding Breath" in delivered_text
        assert "resourceful and capable" in delivered_text
    
    def test_depth_selection_deterministic_branching(self):
        """Test deterministic depth selection between full, theme-only, and scenario"""
        # Test explicit depth selection
        depth = select_protocol_depth(requested_depth='scenario')
        assert depth == 'scenario'
        
        depth = select_protocol_depth(requested_depth='theme')
        assert depth == 'theme'
        
        depth = select_protocol_depth(requested_depth='full')
        assert depth == 'full'
        
        # Test readiness-based selection
        depth = select_protocol_depth(readiness_level='HOLD')
        assert depth == 'scenario'
        
        depth = select_protocol_depth(readiness_level='LATER')
        assert depth == 'theme'
        
        depth = select_protocol_depth(readiness_level='NOW')
        assert depth == 'full'
        
        # Test time-based selection
        depth = select_protocol_depth(time_available=3)
        assert depth == 'scenario'
        
        depth = select_protocol_depth(time_available=10)
        assert depth == 'theme'
        
        depth = select_protocol_depth(time_available=20)
        assert depth == 'full'
    
    def test_depth_selection_switching_produces_correct_output(self):
        """Test that switching between depths produces correct output"""
        protocol_id = 'pacing_adjustment'
        
        # Get text at different depths
        full_text = get_protocol_by_depth(protocol_id, 'full')
        theme_text = get_protocol_by_depth(protocol_id, 'theme')
        scenario_text = get_protocol_by_depth(protocol_id, 'scenario')
        
        # Verify different depths produce different content
        assert full_text != theme_text
        assert full_text != scenario_text
        assert theme_text != scenario_text
        
        # Verify depth-specific content
        assert "Pace Assessment" in full_text
        assert "Assess and adjust your pace" in theme_text
        assert "10 minutes" in scenario_text
    
    def test_scenario_mapping_deterministic_registry(self):
        """Test that scenario string maps to correct protocol ID using static registry"""
        # Test exact scenario matches
        protocol_id = map_scenario_to_protocol('overwhelm')
        assert protocol_id == 'resourcing_mini_walk'
        
        protocol_id = map_scenario_to_protocol('urgency')
        assert protocol_id == 'clearing_entry'
        
        protocol_id = map_scenario_to_protocol('boundary_violation')
        assert protocol_id == 'boundary_setting'
        
        # Test scenario mapping with variations
        protocol_id = map_scenario_to_protocol('stress')
        assert protocol_id == 'resourcing_mini_walk'
        
        protocol_id = map_scenario_to_protocol('confusion')
        assert protocol_id == 'clearing_entry'
        
        # Test default mapping for unknown scenarios
        protocol_id = map_scenario_to_protocol('unknown_scenario')
        assert protocol_id == 'clearing_entry'  # Default protocol
    
    def test_scenario_mapping_comprehensive_coverage(self):
        """Test that scenario mapping covers all expected scenarios"""
        mappings = list_scenario_mappings()
        
        # Verify expected scenarios are present
        scenario_labels = [m.scenario_label for m in mappings]
        
        assert 'overwhelm' in scenario_labels
        assert 'urgency' in scenario_labels
        assert 'boundary_violation' in scenario_labels
        assert 'communication_breakdown' in scenario_labels
        assert 'decision_fatigue' in scenario_labels
        assert 'team_conflict' in scenario_labels
        assert 'personal_crisis' in scenario_labels
        assert 'growth_edge' in scenario_labels
        
        # Verify all mappings have valid protocol IDs
        for mapping in mappings:
            assert mapping.protocol_id in ['resourcing_mini_walk', 'clearing_entry', 'pacing_adjustment', 
                                        'integration_pause', 'deep_listening', 'boundary_setting']
            assert 1 <= mapping.relevance_score <= 10
    
    def test_integrity_gate_stones_alignment_check(self):
        """Test that failing gate produces decline response and halts flow"""
        # Test valid protocol text
        valid_text = """# Test Protocol
        
## Purpose
To test integrity gate functionality with integrity and clarity.
        
## Steps
1. **Step One** - Integrity check
2. **Step Two** - Clarity verification
        
## Completion
When integrity is confirmed, proceed."""
        
        integrity_result = validate_protocol_delivery(valid_text)
        assert integrity_result.passed
        assert integrity_result.stones_aligned
        assert integrity_result.coherent
        
        # Test protocol text that fails Stones alignment
        misaligned_text = """# Problematic Protocol
        
## Purpose
To test manipulation and pressure tactics.
        
## Steps
1. **Step One** - Apply pressure
2. **Step Two** - Create confusion
        
## Completion
When manipulation succeeds, proceed."""
        
        integrity_result = validate_protocol_delivery(misaligned_text)
        assert not integrity_result.passed
        assert not integrity_result.stones_aligned
        assert "Stones principles" in str(integrity_result.notes)
    
    def test_integrity_gate_coherence_check(self):
        """Test coherence checks in integrity gate"""
        # Test coherent protocol text
        coherent_text = """# Coherent Protocol
        
## Purpose
Clear purpose statement.
        
## Steps
1. **Step One** - Clear instruction
2. **Step Two** - Clear instruction
        
## Completion
Clear completion criteria."""
        
        integrity_result = validate_protocol_delivery(coherent_text)
        assert integrity_result.coherent
        
        # Test incoherent protocol text
        incoherent_text = "This is just random text without structure or coherence."
        
        integrity_result = validate_protocol_delivery(incoherent_text)
        assert not integrity_result.passed
        assert not integrity_result.coherent
        assert "coherence" in str(integrity_result.notes)
    
    def test_completion_marker_always_appended(self):
        """Test that completion marker is always appended exactly once"""
        text = "Sample protocol text"
        result = append_fixed_marker(text)
        
        assert result.endswith(" [[COMPLETE]]")
        assert result == "Sample protocol text [[COMPLETE]]"
        assert result.count("[[COMPLETE]]") == 1
    
    def test_completion_marker_no_variants(self):
        """Test that only the fixed marker is used"""
        text = "Sample text"
        result = append_fixed_marker(text)
        
        # Should only contain the exact marker
        assert "[[COMPLETE]]" in result
        assert result.count("[[COMPLETE]]") == 1  # Only one marker
        assert result == text + " [[COMPLETE]]"  # Exact concatenation
    
    def test_contract_io_compliance_exact_schema(self):
        """Test that output conforms to contract schema exactly"""
        input_data = ProtocolRoomInput(
            session_state_ref='contract-test',
            payload={'protocol_id': 'clearing_entry', 'depth': 'theme'}
        )
        
        room = ProtocolRoom()
        result = room.run_protocol_room(input_data)
        
        # Check required properties
        assert hasattr(result, 'display_text')
        assert hasattr(result, 'next_action')
        assert isinstance(result.display_text, str)
        assert result.next_action == "continue"
        
        # Check no additional properties
        assert len(result.__dict__) == 2
        
        # Check completion marker
        assert result.display_text.endswith(" [[COMPLETE]]")
    
    def test_contract_io_compliance_field_types(self):
        """Test that output field types match contract exactly"""
        input_data = ProtocolRoomInput(
            session_state_ref='types-test',
            payload={'protocol_id': 'resourcing_mini_walk', 'depth': 'scenario'}
        )
        
        room = ProtocolRoom()
        result = room.run_protocol_room(input_data)
        
        # Check exact types
        assert isinstance(result.display_text, str)
        assert result.next_action == "continue"  # Contract only allows "continue"
    
    def test_integration_full_flow_success(self):
        """Test that full protocol flow completes successfully"""
        input_data = ProtocolRoomInput(
            session_state_ref='integration-test',
            payload={
                'scenario': 'overwhelm',
                'depth': 'scenario'
            }
        )
        
        room = ProtocolRoom()
        result = room.run_protocol_room(input_data)
        
        # Should contain protocol information
        assert 'Resourcing Mini Walk' in result.display_text
        assert 'Scenario Entry' in result.display_text
        assert '7 minutes' in result.display_text
        assert result.display_text.endswith(" [[COMPLETE]]")
        assert result.next_action == "continue"
    
    def test_integration_explicit_protocol_request(self):
        """Test explicit protocol request flow"""
        input_data = ProtocolRoomInput(
            session_state_ref='explicit-test',
            payload={
                'protocol_id': 'pacing_adjustment',
                'depth': 'full'
            }
        )
        
        room = ProtocolRoom()
        result = room.run_protocol_room(input_data)
        
        # Should contain full protocol
        assert 'Pacing Adjustment' in result.display_text
        assert 'Full Protocol' in result.display_text
        assert 'Pace Assessment' in result.display_text
        assert result.display_text.endswith(" [[COMPLETE]]")
    
    def test_error_handling_graceful_degradation(self):
        """Test that errors are handled gracefully"""
        # Test with missing protocol
        input_data = ProtocolRoomInput(
            session_state_ref='error-test',
            payload={'protocol_id': 'nonexistent_protocol'}
        )
        
        room = ProtocolRoom()
        result = room.run_protocol_room(input_data)
        
        # Should handle error gracefully
        assert "Error" in result.display_text
        assert result.display_text.endswith(" [[COMPLETE]]")
        assert result.next_action == "continue"
    
    def test_error_handling_no_unhandled_exceptions(self):
        """Test that no unhandled exceptions are thrown"""
        problematic_input = ProtocolRoomInput(
            session_state_ref='exception-test',
            payload=None  # This could cause issues
        )
        
        room = ProtocolRoom()
        
        # Should not throw
        try:
            result = room.run_protocol_room(problematic_input)
            assert result is not None
        except Exception:
            assert False, "Should not throw unhandled exceptions"


class TestRunProtocolRoomFunction:
    """Test suite for standalone run_protocol_room function"""
    
    def test_standalone_function_callable(self):
        """Test that run_protocol_room function is callable as standalone function"""
        input_data = ProtocolRoomInput(
            session_state_ref='standalone-test',
            payload={'protocol_id': 'clearing_entry', 'depth': 'theme'}
        )
        
        result = run_protocol_room(input_data)
        
        assert isinstance(result, ProtocolRoomOutput)
        assert 'display_text' in result
        assert 'next_action' in result
        assert result['next_action'] == "continue"
        assert result['display_text'].endswith(" [[COMPLETE]]")


class TestNoTypeScriptArtifacts:
    """Test suite to ensure no TypeScript artifacts remain"""
    
    def test_no_typescript_files_exist(self):
        """Test that no .ts files exist in the protocol room"""
        import os
        
        protocol_room_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(protocol_room_dir)
        
        # Check for .ts files
        ts_files = []
        for root, dirs, files in os.walk(parent_dir):
            for file in files:
                if file.endswith('.ts'):
                    ts_files.append(os.path.join(root, file))
        
        assert len(ts_files) == 0, f"TypeScript files found: {ts_files}"
    
    def test_no_typescript_configs_exist(self):
        """Test that no TypeScript config files exist"""
        import os
        
        protocol_room_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(protocol_room_dir)
        parent_parent_dir = os.path.dirname(parent_dir)
        
        # Check for TypeScript config files
        ts_configs = []
        for root, dirs, files in os.walk(parent_parent_dir):
            for file in files:
                if file in ['package.json', 'tsconfig.json', 'jest.config.js']:
                    ts_configs.append(os.path.join(root, file))
        
        assert len(ts_configs) == 0, f"TypeScript configs found: {ts_configs}"
    
    def test_no_node_modules_exist(self):
        """Test that no node_modules directory exists"""
        import os
        
        protocol_room_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(protocol_room_dir)
        parent_parent_dir = os.path.dirname(parent_dir)
        
        # Check for node_modules
        node_modules_path = os.path.join(parent_parent_dir, 'node_modules')
        assert not os.path.exists(node_modules_path), "node_modules directory found"
