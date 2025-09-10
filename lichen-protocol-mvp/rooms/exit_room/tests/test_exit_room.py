"""
Exit Room Test Suite
Comprehensive testing for all Exit Room functionality
"""

import pytest
from datetime import datetime
from rooms.exit_room.exit_room import ExitRoom, run_exit_room
from rooms.exit_room.contract_types import (
    ExitRoomInput, ExitRoomOutput, ExitReason, ExitDiagnostics,
    MemoryCommitData, SessionState, ExitRoomState, DeclineReason,
    DeclineResponse, ExitOperationResult
)
from rooms.exit_room.completion import CompletionEnforcement
from rooms.exit_room.diagnostics import ExitDiagnosticsCapture
from rooms.exit_room.memory_commit import MemoryCommit
from rooms.exit_room.reset import StateReset


class TestExitRoomContractTypes:
    """Test contract types and data structures"""
    
    def test_exit_reason_enum(self):
        """Test ExitReason enum values"""
        assert ExitReason.NORMAL_COMPLETION.value == "normal_completion"
        assert ExitReason.ABORTED.value == "aborted"
        assert ExitReason.FORCE_CLOSED.value == "force_closed"
        assert ExitReason.ERROR_CONDITION.value == "error_condition"
    
    def test_decline_reason_enum(self):
        """Test DeclineReason enum values"""
        assert DeclineReason.COMPLETION_NOT_SATISFIED.value == "completion_not_satisfied"
        assert DeclineReason.DIAGNOSTICS_FAILED.value == "diagnostics_failed"
        assert DeclineReason.MEMORY_COMMIT_FAILED.value == "memory_commit_failed"
        assert DeclineReason.STATE_RESET_FAILED.value == "state_reset_failed"
        assert DeclineReason.INVALID_INPUT.value == "invalid_input"
    
    def test_exit_diagnostics_creation(self):
        """Test ExitDiagnostics creation"""
        diagnostics = ExitDiagnostics(
            session_id="test_session",
            exit_reason=ExitReason.NORMAL_COMPLETION,
            completion_satisfied=True,
            diagnostics_captured=True,
            memory_committed=False,
            state_reset=False
        )
        
        assert diagnostics.session_id == "test_session"
        assert diagnostics.exit_reason == ExitReason.NORMAL_COMPLETION
        assert diagnostics.completion_satisfied is True
        assert diagnostics.diagnostics_captured is True
        assert diagnostics.memory_committed is False
        assert diagnostics.state_reset is False
    
    def test_memory_commit_data_creation(self):
        """Test MemoryCommitData creation"""
        diagnostics = ExitDiagnostics(
            session_id="test_session",
            exit_reason=ExitReason.NORMAL_COMPLETION,
            completion_satisfied=True,
            diagnostics_captured=True,
            memory_committed=False,
            state_reset=False
        )
        
        commit_data = MemoryCommitData(
            session_id="test_session",
            exit_reason=ExitReason.NORMAL_COMPLETION,
            diagnostics=diagnostics,
            closure_flag=True
        )
        
        assert commit_data.session_id == "test_session"
        assert commit_data.closure_flag is True
        assert commit_data.diagnostics == diagnostics
    
    def test_exit_room_input_output(self):
        """Test ExitRoomInput and ExitRoomOutput"""
        input_data = ExitRoomInput(
            session_state_ref="test_session",
            payload={"test": "data"}
        )
        
        output_data = ExitRoomOutput(
            display_text="Test output",
            next_action="continue"
        )
        
        assert input_data.session_state_ref == "test_session"
        assert input_data.payload == {"test": "data"}
        assert output_data.display_text == "Test output"
        assert output_data.next_action == "continue"
    
    def test_session_state_creation(self):
        """Test SessionState creation"""
        session = SessionState(
            session_id="test_session",
            is_active=True,
            completion_required=True,
            diagnostics_enabled=True
        )
        
        assert session.session_id == "test_session"
        assert session.is_active is True
        assert session.completion_required is True
        assert session.diagnostics_enabled is True
        assert isinstance(session.temporary_buffers, dict)
        assert isinstance(session.session_data, dict)


class TestCompletionEnforcement:
    """Test completion enforcement functionality"""
    
    def test_validate_completion_requirements_success(self):
        """Test successful completion validation"""
        session = SessionState(
            session_id="test_session",
            completion_required=True
        )
        
        payload = {
            "completion_confirmed": True,
            "session_goals_met": True
        }
        
        is_satisfied, decline = CompletionEnforcement.validate_completion_requirements(
            session, payload
        )
        
        assert is_satisfied is True
        assert decline is None
    
    def test_validate_completion_requirements_failure(self):
        """Test completion validation failure"""
        session = SessionState(
            session_id="test_session",
            completion_required=True
        )
        
        payload = {
            "completion_confirmed": False
        }
        
        is_satisfied, decline = CompletionEnforcement.validate_completion_requirements(
            session, payload
        )
        
        assert is_satisfied is False
        assert decline is not None
        assert decline.reason == DeclineReason.COMPLETION_NOT_SATISFIED
    
    def test_completion_not_required(self):
        """Test completion when not required"""
        session = SessionState(
            session_id="test_session",
            completion_required=False
        )
        
        is_satisfied, decline = CompletionEnforcement.validate_completion_requirements(
            session, None
        )
        
        assert is_satisfied is True
        assert decline is None
    
    def test_comprehensive_completion_validation(self):
        """Test comprehensive completion validation"""
        session = SessionState(
            session_id="test_session",
            completion_required=True
        )
        
        payload = {
            "completion_confirmed": True,
            "completion_quality": "comprehensive",
            "session_goals_met": True,
            "integration_complete": True,
            "commitments_recorded": True,
            "reflection_done": True
        }
        
        is_satisfied, decline = CompletionEnforcement.validate_completion_requirements(
            session, payload
        )
        
        assert is_satisfied is True
        assert decline is None
    
    def test_comprehensive_completion_failure(self):
        """Test comprehensive completion validation failure"""
        session = SessionState(
            session_id="test_session",
            completion_required=True
        )
        
        payload = {
            "completion_confirmed": True,
            "completion_quality": "comprehensive",
            "session_goals_met": True,
            "integration_complete": False,  # Missing
            "commitments_recorded": True,
            "reflection_done": True
        }
        
        is_satisfied, decline = CompletionEnforcement.validate_completion_requirements(
            session, payload
        )
        
        assert is_satisfied is False
        assert decline is not None
        assert "integration_complete" in decline.required_fields
    
    def test_can_bypass_completion(self):
        """Test completion bypass for force exits"""
        session = SessionState(session_id="test_session")
        
        # Force closed should bypass
        payload = {"exit_reason": "force_closed"}
        assert CompletionEnforcement.can_bypass_completion(session, payload) is True
        
        # Normal exit should not bypass
        payload = {"exit_reason": "normal_completion"}
        assert CompletionEnforcement.can_bypass_completion(session, payload) is False
        
        # No payload should not bypass
        assert CompletionEnforcement.can_bypass_completion(session, None) is False


class TestExitDiagnosticsCapture:
    """Test diagnostics capture functionality"""
    
    def test_capture_exit_diagnostics_success(self):
        """Test successful diagnostics capture"""
        session = SessionState(
            session_id="test_session",
            created_at=datetime.now()
        )
        
        diagnostics = ExitDiagnosticsCapture.capture_exit_diagnostics(
            session, ExitReason.NORMAL_COMPLETION, None
        )
        
        assert diagnostics.session_id == "test_session"
        assert diagnostics.exit_reason == ExitReason.NORMAL_COMPLETION
        assert diagnostics.diagnostics_captured is True
        assert diagnostics.session_duration is not None
    
    def test_validate_diagnostics_capture_success(self):
        """Test successful diagnostics validation"""
        diagnostics = ExitDiagnostics(
            session_id="test_session",
            exit_reason=ExitReason.NORMAL_COMPLETION,
            completion_satisfied=True,
            diagnostics_captured=True,
            memory_committed=False,
            state_reset=False
        )
        
        is_valid, decline = ExitDiagnosticsCapture.validate_diagnostics_capture(diagnostics)
        
        assert is_valid is True
        assert decline is None
    
    def test_validate_diagnostics_capture_failure(self):
        """Test diagnostics validation failure"""
        diagnostics = ExitDiagnostics(
            session_id="",  # Missing session ID
            exit_reason=ExitReason.NORMAL_COMPLETION,
            completion_satisfied=True,
            diagnostics_captured=True,
            memory_committed=False,
            state_reset=False
        )
        
        is_valid, decline = ExitDiagnosticsCapture.validate_diagnostics_capture(diagnostics)
        
        assert is_valid is False
        assert decline is not None
        assert decline.reason == DeclineReason.DIAGNOSTICS_FAILED
    
    def test_capture_session_metrics(self):
        """Test session metrics capture"""
        session = SessionState(
            session_id="test_session",
            is_active=True,
            completion_required=True,
            diagnostics_enabled=True
        )
        session.temporary_buffers["buffer1"] = "data1"
        session.session_data["data1"] = "value1"
        
        metrics = ExitDiagnosticsCapture.capture_session_metrics(session)
        
        assert metrics["session_id"] == "test_session"
        assert metrics["is_active"] is True
        assert metrics["temporary_buffers_count"] == 1
        assert metrics["session_data_count"] == 1
        assert "buffer1" in metrics["buffer_types"]
        assert "data1" in metrics["data_types"]


class TestMemoryCommit:
    """Test memory commit functionality"""
    
    def test_prepare_memory_commit_success(self):
        """Test successful memory commit preparation"""
        session = SessionState(session_id="test_session")
        diagnostics = ExitDiagnostics(
            session_id="test_session",
            exit_reason=ExitReason.NORMAL_COMPLETION,
            completion_satisfied=True,
            diagnostics_captured=True,
            memory_committed=False,
            state_reset=False
        )
        
        commit_data = MemoryCommit.prepare_memory_commit(session, diagnostics, None)
        
        assert commit_data.session_id == "test_session"
        assert commit_data.closure_flag is True
        assert commit_data.diagnostics == diagnostics
    
    def test_validate_memory_commit_success(self):
        """Test successful memory commit validation"""
        diagnostics = ExitDiagnostics(
            session_id="test_session",
            exit_reason=ExitReason.NORMAL_COMPLETION,
            completion_satisfied=True,
            diagnostics_captured=True,
            memory_committed=False,
            state_reset=False
        )
        
        commit_data = MemoryCommitData(
            session_id="test_session",
            exit_reason=ExitReason.NORMAL_COMPLETION,
            diagnostics=diagnostics,
            closure_flag=True
        )
        
        is_valid, decline = MemoryCommit.validate_memory_commit(commit_data)
        
        assert is_valid is True
        assert decline is None
    
    def test_validate_memory_commit_failure(self):
        """Test memory commit validation failure"""
        commit_data = MemoryCommitData(
            session_id="",  # Missing session ID
            exit_reason=ExitReason.NORMAL_COMPLETION,
            diagnostics=None,  # Missing diagnostics
            closure_flag=True
        )
        
        is_valid, decline = MemoryCommit.validate_memory_commit(commit_data)
        
        assert is_valid is False
        assert decline is not None
        assert decline.reason == DeclineReason.MEMORY_COMMIT_FAILED
    
    def test_execute_memory_commit_success(self):
        """Test successful memory commit execution"""
        diagnostics = ExitDiagnostics(
            session_id="test_session",
            exit_reason=ExitReason.NORMAL_COMPLETION,
            completion_satisfied=True,
            diagnostics_captured=True,
            memory_committed=False,
            state_reset=False
        )
        
        commit_data = MemoryCommitData(
            session_id="test_session",
            exit_reason=ExitReason.NORMAL_COMPLETION,
            diagnostics=diagnostics,
            closure_flag=True
        )
        
        success, error_message = MemoryCommit.execute_memory_commit(commit_data)
        
        assert success is True
        assert error_message is None
        assert commit_data.diagnostics.memory_committed is True


class TestStateReset:
    """Test state reset functionality"""
    
    def test_reset_session_state_success(self):
        """Test successful session state reset"""
        session = SessionState(
            session_id="test_session",
            is_active=True
        )
        session.temporary_buffers["buffer1"] = "data1"
        session.session_data["data1"] = "value1"
        
        diagnostics = ExitDiagnostics(
            session_id="test_session",
            exit_reason=ExitReason.NORMAL_COMPLETION,
            completion_satisfied=True,
            diagnostics_captured=True,
            memory_committed=True,
            state_reset=False
        )
        
        success, error_message = StateReset.reset_session_state(session, diagnostics)
        
        assert success is True
        assert error_message is None
        assert session.is_active is False
        assert len(session.temporary_buffers) == 0
        assert len(session.session_data) == 0
        assert diagnostics.state_reset is True
    
    def test_validate_state_reset_success(self):
        """Test successful state reset validation"""
        session = SessionState(
            session_id="test_session",
            is_active=False
        )
        
        diagnostics = ExitDiagnostics(
            session_id="test_session",
            exit_reason=ExitReason.NORMAL_COMPLETION,
            completion_satisfied=True,
            diagnostics_captured=True,
            memory_committed=True,
            state_reset=True
        )
        
        is_valid, decline = StateReset.validate_state_reset(session, diagnostics)
        
        assert is_valid is True
        assert decline is None
    
    def test_validate_state_reset_failure(self):
        """Test state reset validation failure"""
        session = SessionState(
            session_id="test_session",
            is_active=True  # Still active
        )
        
        diagnostics = ExitDiagnostics(
            session_id="test_session",
            exit_reason=ExitReason.NORMAL_COMPLETION,
            completion_satisfied=True,
            diagnostics_captured=True,
            memory_committed=True,
            state_reset=False
        )
        
        is_valid, decline = StateReset.validate_state_reset(session, diagnostics)
        
        assert is_valid is False
        assert decline is not None
        assert decline.reason == DeclineReason.STATE_RESET_FAILED
    
    def test_can_reenter_session(self):
        """Test session re-entry capability"""
        session = SessionState(
            session_id="test_session",
            is_active=False
        )
        
        assert StateReset.can_reenter_session(session) is True
        
        session.is_active = True
        assert StateReset.can_reenter_session(session) is False
        
        session.is_active = False
        session.temporary_buffers["buffer1"] = "data1"
        assert StateReset.can_reenter_session(session) is False


class TestExitRoomIntegration:
    """Test Exit Room integration and orchestration"""
    
    def test_normal_completion_exit_success(self):
        """Test successful normal completion exit"""
        room = ExitRoom()
        
        input_data = ExitRoomInput(
            session_state_ref="test_session",
            payload={
                "completion_confirmed": True,
                "session_goals_met": True
            }
        )
        
        result = room.process_exit(input_data)
        
        assert result.next_action == "continue"
        assert "Session Successfully Terminated" in result.display_text
        assert "✅ Completion requirements enforced" in result.display_text
        assert "✅ Exit diagnostics captured" in result.display_text
        assert "✅ Final state committed to memory" in result.display_text
        assert "✅ Session state reset for clean re-entry" in result.display_text
    
    def test_completion_failure_exit(self):
        """Test exit failure due to completion requirements"""
        room = ExitRoom()
        
        input_data = ExitRoomInput(
            session_state_ref="test_session",
            payload={
                "completion_confirmed": False
            }
        )
        
        result = room.process_exit(input_data)
        
        assert result.next_action == "continue"
        assert "Session Termination Failed" in result.display_text
        assert "Completion confirmation must be explicitly provided" in result.display_text
    
    def test_force_exit_success(self):
        """Test successful force exit (bypasses completion)"""
        room = ExitRoom()
        
        input_data = ExitRoomInput(
            session_state_ref="test_session",
            payload={
                "exit_reason": "force_closed",
                "force_exit": True
            }
        )
        
        result = room.process_exit(input_data)
        
        assert result.next_action == "continue"
        assert "Session Successfully Terminated" in result.display_text
    
    def test_error_condition_exit(self):
        """Test error condition exit"""
        room = ExitRoom()
        
        input_data = ExitRoomInput(
            session_state_ref="test_session",
            payload={
                "exit_reason": "error_condition",
                "has_errors": True,
                "errors": ["Test error"]
            }
        )
        
        result = room.process_exit(input_data)
        
        assert result.next_action == "continue"
        assert "Session Successfully Terminated" in result.display_text
    
    def test_invalid_input_handling(self):
        """Test handling of invalid input"""
        room = ExitRoom()
        
        input_data = ExitRoomInput(
            session_state_ref="",  # Empty session ref
            payload=None
        )
        
        result = room.process_exit(input_data)
        
        assert result.next_action == "continue"
        assert "Session Termination Failed" in result.display_text
        assert "Invalid input" in result.display_text
    
    def test_room_status_tracking(self):
        """Test room status tracking"""
        room = ExitRoom()
        
        # Initial status
        status = room.get_room_status()
        assert status["room_id"] == "exit_room"
        assert status["completion_enforced"] is False
        assert status["diagnostics_captured"] is False
        assert status["memory_committed"] is False
        assert status["state_reset"] is False
        assert status["active_sessions"] == 0
        assert status["total_sessions"] == 0
        
        # Process a successful exit
        input_data = ExitRoomInput(
            session_state_ref="test_session",
            payload={
                "completion_confirmed": True,
                "session_goals_met": True
            }
        )
        
        room.process_exit(input_data)
        
        # Check updated status
        status = room.get_room_status()
        assert status["completion_enforced"] is True
        assert status["diagnostics_captured"] is True
        assert status["memory_committed"] is True
        assert status["state_reset"] is True
        assert status["total_sessions"] == 1
        assert status["active_sessions"] == 0  # Session marked inactive after reset
    
    def test_session_status_tracking(self):
        """Test session status tracking"""
        room = ExitRoom()
        
        # Process a session
        input_data = ExitRoomInput(
            session_state_ref="test_session",
            payload={
                "completion_confirmed": True,
                "session_goals_met": True
            }
        )
        
        room.process_exit(input_data)
        
        # Get session status
        session_status = room.get_session_status("test_session")
        assert session_status is not None
        assert session_status["session_id"] == "test_session"
        assert session_status["is_active"] is False  # Should be inactive after reset
        assert session_status["temporary_buffers_count"] == 0
        assert session_status["session_data_count"] == 0
    
    def test_multiple_sessions(self):
        """Test handling multiple sessions"""
        room = ExitRoom()
        
        # Process multiple sessions
        sessions = ["session_1", "session_2", "session_3"]
        
        for session_id in sessions:
            input_data = ExitRoomInput(
                session_state_ref=session_id,
                payload={
                    "completion_confirmed": True,
                    "session_goals_met": True
                }
            )
            room.process_exit(input_data)
        
        # Check room status
        status = room.get_room_status()
        assert status["total_sessions"] == 3
        assert status["active_sessions"] == 0  # All sessions should be inactive
    
    def test_run_exit_room_function(self):
        """Test the convenience run_exit_room function"""
        input_data = ExitRoomInput(
            session_state_ref="test_session",
            payload={
                "completion_confirmed": True,
                "session_goals_met": True
            }
        )
        
        result = run_exit_room(input_data)
        
        assert isinstance(result, dict)
        assert result['next_action'] == "continue"
        assert "Session Successfully Terminated" in result['display_text']


class TestExitRoomEdgeCases:
    """Test Exit Room edge cases and error conditions"""
    
    def test_missing_payload_handling(self):
        """Test handling of missing payload"""
        room = ExitRoom()
        
        input_data = ExitRoomInput(
            session_state_ref="test_session",
            payload=None
        )
        
        result = room.process_exit(input_data)
        
        assert result.next_action == "continue"
        assert "Session Termination Failed" in result.display_text
        assert "Completion confirmation required" in result.display_text
    
    def test_empty_payload_handling(self):
        """Test handling of empty payload"""
        room = ExitRoom()
        
        input_data = ExitRoomInput(
            session_state_ref="test_session",
            payload={}
        )
        
        result = room.process_exit(input_data)
        
        assert result.next_action == "continue"
        assert "Session Termination Failed" in result.display_text
        assert "Completion confirmation required" in result.display_text
    
    def test_invalid_exit_reason_handling(self):
        """Test handling of invalid exit reason"""
        room = ExitRoom()
        
        input_data = ExitRoomInput(
            session_state_ref="test_session",
            payload={
                "exit_reason": "invalid_reason",
                "completion_confirmed": True,
                "session_goals_met": True
            }
        )
        
        result = room.process_exit(input_data)
        
        # Should still succeed but use ERROR_CONDITION
        assert result.next_action == "continue"
        assert "Session Successfully Terminated" in result.display_text
    
    def test_session_reentry_after_exit(self):
        """Test re-entering a session after exit"""
        room = ExitRoom()
        
        # First exit
        input_data = ExitRoomInput(
            session_state_ref="test_session",
            payload={
                "completion_confirmed": True,
                "session_goals_met": True
            }
        )
        
        first_result = room.process_exit(input_data)
        assert "Session Successfully Terminated" in first_result.display_text
        
        # Try to re-enter the same session
        reentry_result = room.process_exit(input_data)
        assert "Session Successfully Terminated" in reentry_result.display_text
        
        # Check that it's treated as a new session
        status = room.get_room_status()
        assert status["total_sessions"] == 1  # Still one session reference
        assert status["active_sessions"] == 0  # But inactive


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
