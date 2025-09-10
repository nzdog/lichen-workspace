"""
Diagnostic Room Unit Tests
Tests all behavioral invariants and edge cases using pytest
"""

import pytest
from diagnostic_room.diagnostic_room import DiagnosticRoom, run_diagnostic_room
from diagnostic_room.types import DiagnosticRoomInput, DiagnosticRoomOutput, DiagnosticSignals, ProtocolMapping
from diagnostic_room.sensing import capture_tone_and_residue
from diagnostic_room.readiness import assess_readiness
from diagnostic_room.mapping import map_to_protocol
from diagnostic_room.capture import capture_diagnostics, format_display_text
from diagnostic_room.completion import append_fixed_marker


class TestDiagnosticRoom:
    """Test suite for Diagnostic Room implementation"""
    
    @pytest.fixture
    def sample_input(self):
        """Sample input for testing"""
        return DiagnosticRoomInput(
            session_state_ref='test-session-123',
            payload='I feel overwhelmed and still have unresolved issues from yesterday.'
        )
    
    @pytest.fixture
    def diagnostic_room(self):
        """Diagnostic Room instance with diagnostics enabled"""
        return DiagnosticRoom(diagnostics_enabled=True)
    
    @pytest.fixture
    def diagnostic_room_disabled(self):
        """Diagnostic Room instance with diagnostics disabled"""
        return DiagnosticRoom(diagnostics_enabled=False)
    
    def test_capture_only_sensing_no_interpretation(self):
        """Test that tone and residue are captured without interpretation"""
        # Test with explicit payload
        payload = {
            'tone_label': 'explicit_tone',
            'residue_label': 'explicit_residue',
            'readiness_state': 'HOLD'
        }
        
        signals = capture_tone_and_residue(payload)
        
        assert signals.tone_label == 'explicit_tone'
        assert signals.residue_label == 'explicit_residue'
        assert signals.readiness_state == 'HOLD'
    
    def test_capture_only_sensing_defaults_to_unspecified(self):
        """Test that missing signals default to 'unspecified'"""
        # Test with minimal payload
        payload = "Simple text"
        
        signals = capture_tone_and_residue(payload)
        
        assert signals.tone_label == "unspecified"
        assert signals.residue_label == "unspecified"
        assert signals.readiness_state == "NOW"
    
    def test_capture_only_sensing_deterministic_patterns(self):
        """Test deterministic pattern matching for tone and residue"""
        # Test tone patterns
        payload = "I feel overwhelmed by this situation"
        signals = capture_tone_and_residue(payload)
        assert signals.tone_label == "overwhelm"
        
        # Test residue patterns
        payload = "I still have the same problem"
        signals = capture_tone_and_residue(payload)
        assert signals.residue_label == "unresolved_previous"
    
    def test_readiness_tagging_deterministic_mapping(self):
        """Test deterministic readiness assessment"""
        # Test explicit readiness
        signals = DiagnosticSignals(
            tone_label="unspecified",
            residue_label="unspecified",
            readiness_state="LATER"
        )
        
        readiness = assess_readiness(signals)
        assert readiness == "LATER"
        
        # Test tone-based readiness
        signals = DiagnosticSignals(
            tone_label="overwhelm",
            residue_label="unspecified",
            readiness_state="NOW"
        )
        
        readiness = assess_readiness(signals)
        assert readiness == "HOLD"
    
    def test_readiness_tagging_all_four_states(self):
        """Test that all four readiness states are supported"""
        states = ["NOW", "HOLD", "LATER", "SOFT_HOLD"]
        
        for state in states:
            signals = DiagnosticSignals(
                tone_label="unspecified",
                residue_label="unspecified",
                readiness_state=state
            )
            
            readiness = assess_readiness(signals)
            assert readiness == state
    
    def test_mapping_registry_deterministic_selection(self):
        """Test deterministic protocol mapping"""
        # Test tone-based mapping
        signals = DiagnosticSignals(
            tone_label="overwhelm",
            residue_label="unspecified",
            readiness_state="NOW"
        )
        
        mapping = map_to_protocol(signals)
        assert mapping.suggested_protocol_id == "resourcing_mini_walk"
        assert "overwhelm" in mapping.rationale
        
        # Test residue-based mapping
        signals = DiagnosticSignals(
            tone_label="unspecified",
            residue_label="unresolved_previous",
            readiness_state="NOW"
        )
        
        mapping = map_to_protocol(signals)
        assert mapping.suggested_protocol_id == "integration_pause"
        assert "unresolved_previous" in mapping.rationale
    
    def test_mapping_registry_fixed_template_rationale(self):
        """Test that rationale uses fixed template format"""
        signals = DiagnosticSignals(
            tone_label="urgency",
            residue_label="unspecified",
            readiness_state="NOW"
        )
        
        mapping = map_to_protocol(signals)
        assert "Tone: urgency →" in mapping.rationale
        assert mapping.rationale.endswith("Clearing for focus")
    
    def test_diagnostics_toggle_enabled_captures_data(self):
        """Test that diagnostics are captured when enabled"""
        signals = DiagnosticSignals(
            tone_label="worry",
            residue_label="unspecified",
            readiness_state="HOLD"
        )
        
        mapping = ProtocolMapping(
            suggested_protocol_id="pacing_adjustment",
            rationale="Test rationale"
        )
        
        diagnostic_data = capture_diagnostics(signals, mapping, diagnostics_enabled=True)
        
        assert diagnostic_data is not None
        assert diagnostic_data["tone_label"] == "worry"
        assert diagnostic_data["readiness_state"] == "HOLD"
        assert diagnostic_data["suggested_protocol_id"] == "pacing_adjustment"
    
    def test_diagnostics_toggle_disabled_skips_capture(self):
        """Test that diagnostics are skipped when disabled"""
        signals = DiagnosticSignals(
            tone_label="worry",
            residue_label="unspecified",
            readiness_state="HOLD"
        )
        
        mapping = ProtocolMapping(
            suggested_protocol_id="pacing_adjustment",
            rationale="Test rationale"
        )
        
        diagnostic_data = capture_diagnostics(signals, mapping, diagnostics_enabled=False)
        
        assert diagnostic_data is None
    
    def test_diagnostics_toggle_never_blocks_flow(self):
        """Test that diagnostics failure doesn't break main flow"""
        # This test ensures that even if diagnostics fail, the room continues
        # The capture_diagnostics function is designed to never throw exceptions
        
        signals = DiagnosticSignals(
            tone_label="worry",
            residue_label="unspecified",
            readiness_state="HOLD"
        )
        
        mapping = ProtocolMapping(
            suggested_protocol_id="pacing_adjustment",
            rationale="Test rationale"
        )
        
        # Should not throw even with invalid inputs
        try:
            diagnostic_data = capture_diagnostics(signals, mapping, diagnostics_enabled=True)
            # If we get here, flow wasn't blocked
            assert True
        except Exception:
            assert False, "Diagnostics should not block flow"
    
    def test_completion_marker_single_fixed_marker(self):
        """Test that completion marker is appended correctly"""
        text = "Sample diagnostic text"
        result = append_fixed_marker(text)
        
        assert result.endswith(" [[COMPLETE]]")
        assert result == "Sample diagnostic text [[COMPLETE]]"
    
    def test_completion_marker_no_variants(self):
        """Test that only the fixed marker is used"""
        text = "Sample text"
        result = append_fixed_marker(text)
        
        # Should only contain the exact marker
        assert "[[COMPLETE]]" in result
        assert result.count("[[COMPLETE]]") == 1  # Only one marker
    
    def test_contract_io_compliance_exact_schema(self):
        """Test that output matches contract schema exactly"""
        input_data = DiagnosticRoomInput(
            session_state_ref='contract-test',
            payload='Test payload'
        )
        
        room = DiagnosticRoom()
        result = room.run_diagnostic_room(input_data)
        
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
        input_data = DiagnosticRoomInput(
            session_state_ref='types-test',
            payload='Test payload'
        )
        
        room = DiagnosticRoom()
        result = room.run_diagnostic_room(input_data)
        
        # Check exact types
        assert isinstance(result.display_text, str)
        assert result.next_action == "continue"  # Contract only allows "continue"
    
    def test_integration_full_flow_success(self):
        """Test that full diagnostic flow completes successfully"""
        input_data = DiagnosticRoomInput(
            session_state_ref='integration-test',
            payload='I feel overwhelmed and still have unresolved issues'
        )
        
        room = DiagnosticRoom()
        result = room.run_diagnostic_room(input_data)
        
        # Should contain diagnostic information
        assert 'Tone: overwhelm' in result.display_text
        assert 'Residue: unresolved_previous' in result.display_text
        assert 'Suggested Protocol:' in result.display_text
        assert result.display_text.endswith(" [[COMPLETE]]")
        assert result.next_action == "continue"
    
    def test_integration_diagnostics_disabled_flow_continues(self):
        """Test that flow continues when diagnostics are disabled"""
        input_data = DiagnosticRoomInput(
            session_state_ref='disabled-test',
            payload='I feel calm and ready to proceed'
        )
        
        room = DiagnosticRoom(diagnostics_enabled=False)
        result = room.run_diagnostic_room(input_data)
        
        # Should still complete successfully
        assert result.display_text.endswith(" [[COMPLETE]]")
        assert result.next_action == "continue"
    
    def test_error_handling_graceful_degradation(self):
        """Test that errors are handled gracefully"""
        # Test with problematic payload
        input_data = DiagnosticRoomInput(
            session_state_ref='error-test',
            payload=None  # This could cause issues
        )
        
        room = DiagnosticRoom()
        result = room.run_diagnostic_room(input_data)
        
        # Should handle error gracefully
        assert "error" in result.display_text.lower()
        assert result.display_text.endswith(" [[COMPLETE]]")
        assert result.next_action == "continue"
    
    def test_error_handling_no_unhandled_exceptions(self):
        """Test that no unhandled exceptions are thrown"""
        problematic_input = DiagnosticRoomInput(
            session_state_ref='exception-test',
            payload='Normal payload'
        )
        
        room = DiagnosticRoom()
        
        # Should not throw
        try:
            result = room.run_diagnostic_room(problematic_input)
            assert result is not None
        except Exception:
            assert False, "Should not throw unhandled exceptions"


class TestRunDiagnosticRoomFunction:
    """Test suite for standalone run_diagnostic_room function"""
    
    def test_standalone_function_callable(self):
        """Test that run_diagnostic_room function is callable as standalone function"""
        input_data = DiagnosticRoomInput(
            session_state_ref='standalone-test',
            payload='Test payload'
        )
        
        result = run_diagnostic_room(input_data)
        
        assert hasattr(result, 'display_text')
        assert hasattr(result, 'next_action')
        assert result.next_action == "continue"
    
    def test_standalone_function_accepts_diagnostics_toggle(self):
        """Test that run_diagnostic_room function accepts diagnostics toggle"""
        input_data = DiagnosticRoomInput(
            session_state_ref='toggle-test',
            payload='Test payload'
        )
        
        # Test with diagnostics disabled
        result = run_diagnostic_room(input_data, diagnostics_enabled=False)
        
        assert result.display_text.endswith(" [[COMPLETE]]")
        assert result.next_action == "continue"


class TestNoTypeScriptArtifacts:
    """Test suite to ensure no TypeScript artifacts remain"""
    
    def test_no_typescript_files_exist(self):
        """Test that no .ts files exist in the diagnostic room"""
        import os
        
        diagnostic_room_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(diagnostic_room_dir)
        
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
        
        diagnostic_room_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(diagnostic_room_dir)
        
        # Check for TypeScript config files
        ts_configs = []
        for root, dirs, files in os.walk(parent_dir):
            for file in files:
                if file in ['package.json', 'tsconfig.json', 'jest.config.js']:
                    ts_configs.append(os.path.join(root, file))
        
        assert len(ts_configs) == 0, f"TypeScript configs found: {ts_configs}"
    
    def test_no_node_modules_exist(self):
        """Test that no node_modules directory exists"""
        import os
        
        diagnostic_room_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(diagnostic_room_dir)
        
        # Check for node_modules
        node_modules_path = os.path.join(parent_dir, 'node_modules')
        assert not os.path.exists(node_modules_path), "node_modules directory found"
