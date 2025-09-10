"""
Test Suite for Walk Room
Comprehensive testing of sequence enforcement, pacing, diagnostics, and completion
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rooms.walk_room.walk_room import WalkRoom, run_walk_room
from rooms.walk_room.contract_types import (
    WalkRoomInput, WalkRoomOutput, WalkStep, WalkState, 
    PaceState, StepDiagnostics, ProtocolStructure, WalkSession
)
from rooms.walk_room.sequencer import StepSequencer
from rooms.walk_room.pacing import PaceGovernor
from rooms.walk_room.step_diag import StepDiagnosticCapture
from rooms.walk_room.completion import WalkCompletion


class TestWalkRoom:
    """Test Walk Room main functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.room = WalkRoom()
        self.test_steps = [
            WalkStep(
                step_index=0,
                title="Grounding Breath",
                content="Take 3 deep breaths",
                description="Begin with grounding breath practice",
                estimated_time=2
            ),
            WalkStep(
                step_index=1,
                title="Resource Inventory",
                content="List 3 personal resources",
                description="Identify your current resources",
                estimated_time=3
            ),
            WalkStep(
                step_index=2,
                title="Centering Practice",
                content="Find your center point",
                description="Connect with your center",
                estimated_time=2
            )
        ]
    
    def test_start_walk_creates_session(self):
        """Test that starting a walk creates a session"""
        input_data = WalkRoomInput(
            session_state_ref='test-session',
            payload={
                'protocol_id': 'test_protocol',
                'title': 'Test Protocol',
                'steps': [
                    {
                        'title': 'Step 1',
                        'content': 'Content 1',
                        'description': 'Description 1'
                    }
                ]
            }
        )
        
        result = self.room.run_walk_room(input_data)
        
        # Should return first step
        assert 'Step 1' in result.display_text
        assert result.next_action == "continue"
        
        # Session should be created
        session = self.room._get_session('test-session')
        assert session is not None
        assert session.protocol_id == 'test_protocol'
        assert session.current_step_index == 0
    
    def test_sequence_enforcement_one_step_at_time(self):
        """Test that steps are delivered one at a time"""
        # Start walk
        start_input = WalkRoomInput(
            session_state_ref='sequence-test',
            payload={
                'protocol_id': 'sequence_test',
                'steps': [
                    {'title': 'Step 1', 'description': 'First step'},
                    {'title': 'Step 2', 'description': 'Second step'},
                    {'title': 'Step 3', 'description': 'Third step'}
                ]
            }
        )
        
        self.room.run_walk_room(start_input)
        
        # Should start with step 1
        current_input = WalkRoomInput(
            session_state_ref='sequence-test',
            payload={}
        )
        
        result = self.room.run_walk_room(current_input)
        assert 'Step 1' in result.display_text
        assert 'Step 2' not in result.display_text
        assert 'Step 3' not in result.display_text
    
    def test_advance_step_requires_pace_setting(self):
        """Test that advancing requires pace to be set"""
        # Start walk
        start_input = WalkRoomInput(
            session_state_ref='advance-test',
            payload={
                'protocol_id': 'advance_test',
                'steps': [
                    {'title': 'Step 1', 'description': 'First step'},
                    {'title': 'Step 2', 'description': 'Second step'}
                ]
            }
        )
        
        self.room.run_walk_room(start_input)
        
        # Try to advance without setting pace
        advance_input = WalkRoomInput(
            session_state_ref='advance-test',
            payload={'action': 'advance_step'}
        )
        
        result = self.room.run_walk_room(advance_input)
        # Should return error about pace requirement
        assert 'Walk Room Error' in result.display_text
        assert 'pace must be set' in result.display_text
    
    def test_pacing_governance_mapping(self):
        """Test that pace states map to correct next_action values"""
        # Start walk
        start_input = WalkRoomInput(
            session_state_ref='pacing-test',
            payload={
                'protocol_id': 'pacing_test',
                'steps': [
                    {'title': 'Step 1', 'description': 'First step'},
                    {'title': 'Step 2', 'description': 'Second step'}
                ]
            }
        )
        
        self.room.run_walk_room(start_input)
        
        # Test NOW pace
        now_input = WalkRoomInput(
            session_state_ref='pacing-test',
            payload={'pace': 'NOW'}
        )
        
        result = self.room.run_walk_room(now_input)
        assert result.next_action == "continue"
        
        # Test HOLD pace
        hold_input = WalkRoomInput(
            session_state_ref='pacing-test',
            payload={'pace': 'HOLD'}
        )
        
        result = self.room.run_walk_room(hold_input)
        assert result.next_action == "hold"
        
        # Test LATER pace
        later_input = WalkRoomInput(
            session_state_ref='pacing-test',
            payload={'pace': 'LATER'}
        )
        
        result = self.room.run_walk_room(later_input)
        assert result.next_action == "later"
        
        # Test SOFT_HOLD pace
        soft_hold_input = WalkRoomInput(
            session_state_ref='pacing-test',
            payload={'pace': 'SOFT_HOLD'}
        )
        
        result = self.room.run_walk_room(soft_hold_input)
        assert result.next_action == "hold"
    
    def test_step_diagnostics_capture_only(self):
        """Test that diagnostics are captured without interpretation"""
        # Start walk
        start_input = WalkRoomInput(
            session_state_ref='diagnostics-test',
            payload={
                'protocol_id': 'diagnostics_test',
                'steps': [
                    {'title': 'Step 1', 'description': 'First step'},
                    {'title': 'Step 2', 'description': 'Second step'}
                ]
            }
        )
        
        self.room.run_walk_room(start_input)
        
        # Set pace to capture diagnostics
        pace_input = WalkRoomInput(
            session_state_ref='diagnostics-test',
            payload={'pace': 'NOW'}
        )
        
        self.room.run_walk_room(pace_input)
        
        # Check that diagnostics were captured
        session = self.room._get_session('diagnostics-test')
        assert len(session.diagnostics) == 1
        
        diag = session.diagnostics[0]
        assert diag.step_index == 0
        assert diag.tone_label == "unspecified"
        assert diag.residue_label == "unspecified"
        assert diag.readiness_state == "NOW"
    
    def test_completion_enforcement_blocks_termination(self):
        """Test that completion is enforced before termination"""
        # Start walk
        start_input = WalkRoomInput(
            session_state_ref='completion-test',
            payload={
                'protocol_id': 'completion_test',
                'steps': [
                    {'title': 'Step 1', 'description': 'First step'},
                    {'title': 'Step 2', 'description': 'Second step'}
                ]
            }
        )
        
        self.room.run_walk_room(start_input)
        
        # Set pace for first step
        pace_input = WalkRoomInput(
            session_state_ref='completion-test',
            payload={'pace': 'NOW'}
        )
        
        self.room.run_walk_room(pace_input)
        
        # Advance to second step
        advance_input = WalkRoomInput(
            session_state_ref='completion-test',
            payload={'action': 'advance_step'}
        )
        
        self.room.run_walk_room(advance_input)
        
        # Set pace for second step
        pace_input2 = WalkRoomInput(
            session_state_ref='completion-test',
            payload={'pace': 'NOW'}
        )
        
        self.room.run_walk_room(pace_input2)
        
        # Try to complete without confirmation
        complete_input = WalkRoomInput(
            session_state_ref='completion-test',
            payload={'action': 'confirm_completion'}
        )
        
        result = self.room.run_walk_room(complete_input)
        
        # Should show completion summary with [[COMPLETE]] marker
        assert 'Walk Complete' in result.display_text
        assert '[[COMPLETE]]' in result.display_text
        assert result.next_action == "continue"
    
    def test_contract_io_compliance(self):
        """Test that input/output conforms to contract schema"""
        input_data = WalkRoomInput(
            session_state_ref='contract-test',
            payload={
                'protocol_id': 'contract_test',
                'steps': [
                    {'title': 'Step 1', 'description': 'First step'}
                ]
            }
        )
        
        result = self.room.run_walk_room(input_data)
        
        # Check output structure matches contract
        assert hasattr(result, 'display_text')
        assert hasattr(result, 'next_action')
        assert isinstance(result.display_text, str)
        assert result.next_action == "continue"
        
        # Check no extra fields
        assert len(result.__dict__) == 2
    
    def test_error_containment_structured_declines(self):
        """Test that errors return structured declines without state mutation"""
        # Try to get status without session
        input_data = WalkRoomInput(
            session_state_ref='nonexistent-session',
            payload={'action': 'get_walk_status'}
        )
        
        result = self.room.run_walk_room(input_data)
        
        # Should return error message
        assert 'Walk Room Error' in result.display_text
        assert result.next_action == "continue"
        
        # Should not crash or mutate state
        assert len(self.room.sessions) == 0
    
    def test_invalid_pace_handling(self):
        """Test that invalid pace states are handled gracefully"""
        # Start walk
        start_input = WalkRoomInput(
            session_state_ref='invalid-pace-test',
            payload={
                'protocol_id': 'invalid_pace_test',
                'steps': [
                    {'title': 'Step 1', 'description': 'First step'}
                ]
            }
        )
        
        self.room.run_walk_room(start_input)
        
        # Try invalid pace
        invalid_pace_input = WalkRoomInput(
            session_state_ref='invalid-pace-test',
            payload={'pace': 'INVALID_PACE'}
        )
        
        result = self.room.run_walk_room(invalid_pace_input)
        
        # Should return error
        assert 'Walk Room Error' in result.display_text
        assert 'Invalid pace state' in result.display_text


class TestStepSequencer:
    """Test StepSequencer functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.steps = [
            WalkStep(step_index=0, title="Step 1", content="", description="First step"),
            WalkStep(step_index=1, title="Step 2", content="", description="Second step"),
            WalkStep(step_index=2, title="Step 3", content="", description="Third step")
        ]
        self.sequencer = StepSequencer(self.steps)
    
    def test_initial_state(self):
        """Test initial sequencer state"""
        assert self.sequencer.current_index == 0
        assert self.sequencer.total_steps == 3
        assert self.sequencer.get_current_step() == self.steps[0]
    
    def test_advance_step(self):
        """Test advancing to next step"""
        success, error = self.sequencer.advance_step()
        assert success is True
        assert error is None
        assert self.sequencer.current_index == 1
        assert self.sequencer.get_current_step() == self.steps[1]
    
    def test_cannot_advance_beyond_last(self):
        """Test that advancing beyond last step is blocked"""
        # Advance to last step
        self.sequencer.current_index = 2
        
        success, error = self.sequencer.advance_step()
        assert success is False
        assert "Cannot advance" in error
        assert self.sequencer.current_index == 2  # Unchanged
    
    def test_retreat_step(self):
        """Test retreating to previous step"""
        self.sequencer.current_index = 1
        
        success, error = self.sequencer.retreat_step()
        assert success is True
        assert error is None
        assert self.sequencer.current_index == 0
    
    def test_cannot_retreat_before_first(self):
        """Test that retreating before first step is blocked"""
        success, error = self.sequencer.retreat_step()
        assert success is False
        assert "Cannot retreat" in error
        assert self.sequencer.current_index == 0  # Unchanged
    
    def test_jump_to_step(self):
        """Test jumping to specific step"""
        success, error = self.sequencer.jump_to_step(2)
        assert success is True
        assert error is None
        assert self.sequencer.current_index == 2
    
    def test_jump_to_invalid_step(self):
        """Test jumping to invalid step index"""
        success, error = self.sequencer.jump_to_step(5)
        assert success is False
        assert "Invalid step index" in error
    
    def test_sequence_integrity_validation(self):
        """Test sequence integrity validation"""
        is_valid, errors = self.sequencer.validate_sequence_integrity()
        assert is_valid is True
        assert len(errors) == 0


class TestPaceGovernor:
    """Test PaceGovernor functionality"""
    
    def test_pace_validation(self):
        """Test pace state validation"""
        assert PaceGovernor.validate_pace_state("NOW") is True
        assert PaceGovernor.validate_pace_state("HOLD") is True
        assert PaceGovernor.validate_pace_state("LATER") is True
        assert PaceGovernor.validate_pace_state("SOFT_HOLD") is True
        assert PaceGovernor.validate_pace_state("INVALID") is False
    
    def test_pace_to_action_mapping(self):
        """Test pace to next_action mapping"""
        assert PaceGovernor.map_pace_to_action("NOW") == "continue"
        assert PaceGovernor.map_pace_to_action("HOLD") == "hold"
        assert PaceGovernor.map_pace_to_action("LATER") == "later"
        assert PaceGovernor.map_pace_to_action("SOFT_HOLD") == "hold"
        assert PaceGovernor.map_pace_to_action("INVALID") == "hold"  # Default
    
    def test_can_advance_with_pace(self):
        """Test pace advancement logic"""
        assert PaceGovernor.can_advance_with_pace("NOW") is True
        assert PaceGovernor.can_advance_with_pace("HOLD") is False
        assert PaceGovernor.can_advance_with_pace("LATER") is False
        assert PaceGovernor.can_advance_with_pace("SOFT_HOLD") is False
    
    def test_structural_pause_detection(self):
        """Test structural pause detection"""
        assert PaceGovernor.is_structural_pause("HOLD") is True
        assert PaceGovernor.is_structural_pause("LATER") is True
        assert PaceGovernor.is_structural_pause("NOW") is False
        assert PaceGovernor.is_structural_pause("SOFT_HOLD") is False


class TestStepDiagnosticCapture:
    """Test StepDiagnosticCapture functionality"""
    
    def test_create_step_diagnostics_defaults(self):
        """Test creating diagnostics with defaults"""
        diag = StepDiagnosticCapture.create_step_diagnostics(0)
        
        assert diag.step_index == 0
        assert diag.tone_label == "unspecified"
        assert diag.residue_label == "unspecified"
        assert diag.readiness_state == "NOW"
    
    def test_create_step_diagnostics_with_values(self):
        """Test creating diagnostics with explicit values"""
        diag = StepDiagnosticCapture.create_step_diagnostics(
            1, "calm", "none", "HOLD"
        )
        
        assert diag.step_index == 1
        assert diag.tone_label == "calm"
        assert diag.residue_label == "none"
        assert diag.readiness_state == "HOLD"
    
    def test_validate_diagnostics(self):
        """Test diagnostics validation"""
        valid_diag = StepDiagnosticCapture.create_step_diagnostics(0)
        assert StepDiagnosticCapture.validate_diagnostics(valid_diag) is True
        
        # Invalid step index
        invalid_diag = StepDiagnosticCapture.create_step_diagnostics(0)
        invalid_diag.step_index = "invalid"
        assert StepDiagnosticCapture.validate_diagnostics(invalid_diag) is False
    
    def test_format_diagnostics_summary(self):
        """Test diagnostics summary formatting"""
        diag1 = StepDiagnosticCapture.create_step_diagnostics(0, "calm", "none", "NOW")
        diag2 = StepDiagnosticCapture.create_step_diagnostics(1, "focused", "some", "HOLD")
        
        summary = StepDiagnosticCapture.format_diagnostics_summary([diag1, diag2])
        
        assert "Step 0" in summary
        assert "Step 1" in summary
        assert "calm" in summary
        assert "focused" in summary


class TestWalkCompletion:
    """Test WalkCompletion functionality"""
    
    def test_create_completion_prompt(self):
        """Test completion prompt creation"""
        prompt = WalkCompletion.create_completion_prompt("Test Protocol", 3)
        
        assert "Test Protocol" in prompt.prompt_text
        assert "3 steps" in prompt.prompt_text
        assert prompt.response_required is True
    
    def test_append_completion_marker(self):
        """Test completion marker appending"""
        text = "Walk complete"
        marked_text = WalkCompletion.append_completion_marker(text)
        
        assert marked_text == "Walk complete [[COMPLETE]]"
        assert marked_text.count("[[COMPLETE]]") == 1  # Only once
    
    def test_completion_requirements_validation(self):
        """Test completion requirements validation"""
        steps = [WalkStep(step_index=0, title="Step 1", content="", description="")]
        
        # Valid completion
        is_complete, missing = WalkCompletion.validate_completion_requirements(
            steps, 0, True, True
        )
        assert is_complete is True
        assert len(missing) == 0
        
        # Missing diagnostics
        is_complete, missing = WalkCompletion.validate_completion_requirements(
            steps, 0, False, True
        )
        assert is_complete is False
        assert "Step diagnostics not captured" in missing


class TestNoTypeScriptArtifacts:
    """Test that no TypeScript artifacts exist"""
    
    def test_no_typescript_files_exist(self):
        """Assert that no .ts files exist in the walk_room directory"""
        walk_room_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        for root, dirs, files in os.walk(walk_room_dir):
            for file in files:
                assert not file.endswith('.ts'), f"TypeScript file found: {file}"
    
    def test_no_typescript_configs_exist(self):
        """Assert that no TypeScript config files exist"""
        walk_room_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        config_files = ['tsconfig.json', 'jest.config.js']
        for config in config_files:
            config_path = os.path.join(walk_room_dir, config)
            assert not os.path.exists(config_path), f"TypeScript config found: {config}"
    
    def test_no_node_modules_exist(self):
        """Assert that no node_modules directory exists"""
        walk_room_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        node_modules_path = os.path.join(walk_room_dir, 'node_modules')
        
        assert not os.path.exists(node_modules_path), "node_modules directory found"


class TestRunWalkRoomFunction:
    """Test standalone run_walk_room function"""
    
    def test_standalone_function_callable(self):
        """Test that standalone function is callable"""
        input_data = WalkRoomInput(
            session_state_ref='standalone-test',
            payload={
                'protocol_id': 'standalone_test',
                'steps': [
                    {'title': 'Step 1', 'description': 'First step'}
                ]
            }
        )
        
        result = run_walk_room(input_data)
        
        assert isinstance(result, dict)
        assert 'Step 1' in result['display_text']
        assert result['next_action'] == "continue"
