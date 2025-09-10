from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from .contract_types import (
    ExitRoomInput, ExitRoomOutput, ExitRoomState, SessionState,
    ExitReason, ExitDiagnostics, MemoryCommitData, DeclineResponse
)
from .completion import CompletionEnforcement
from .diagnostics import ExitDiagnosticsCapture
from .memory_commit import MemoryCommit
from .reset import StateReset


class ExitRoom:
    """Main orchestrator for the Exit Room"""
    
    def __init__(self):
        """Initialize the Exit Room"""
        self.room_state = ExitRoomState()
        self.sessions: Dict[str, SessionState] = {}
    
    def process_exit(
        self,
        input_data: ExitRoomInput
    ) -> ExitRoomOutput:
        """
        Process session exit request.
        Orchestrates completion → diagnostics → memory commit → state reset.
        """
        try:
            # Validate input
            if not self._validate_input(input_data):
                return self._create_error_output("Invalid input: session_state_ref is required")
            
            # Get or create session state
            session_state = self._get_or_create_session(input_data.session_state_ref)
            
            # Step 1: Enforce completion requirements
            completion_result = self._enforce_completion(session_state, input_data.payload)
            if not completion_result["success"]:
                return self._create_error_output(completion_result["message"])
            
            # Step 2: Capture exit diagnostics
            diagnostics_result = self._capture_diagnostics(session_state, input_data.payload)
            if not diagnostics_result["success"]:
                return self._create_error_output(diagnostics_result["message"])
            
            # Step 3: Commit to memory
            memory_result = self._commit_to_memory(session_state, diagnostics_result["diagnostics"], input_data.payload)
            if not memory_result["success"]:
                return self._create_error_output(memory_result["message"])
            
            # Step 4: Reset session state
            reset_result = self._reset_session_state(session_state, diagnostics_result["diagnostics"])
            if not reset_result["success"]:
                return self._create_error_output(reset_result["message"])
            
            # Create success output
            return self._create_success_output(
                session_state, 
                diagnostics_result["diagnostics"],
                memory_result["commit_data"]
            )
            
        except Exception as e:
            return self._create_error_output(f"Exit Room error: {str(e)}")
    
    def _validate_input(self, input_data: ExitRoomInput) -> bool:
        """Validate input data"""
        return (input_data.session_state_ref and 
                isinstance(input_data.session_state_ref, str) and
                len(input_data.session_state_ref.strip()) > 0)
    
    def _get_or_create_session(self, session_ref: str) -> SessionState:
        """Get existing session or create new one"""
        if session_ref not in self.sessions:
            self.sessions[session_ref] = SessionState(
                session_id=session_ref,
                is_active=True,
                created_at=datetime.now(),
                last_accessed=datetime.now()
            )
        else:
            # Update last accessed
            self.sessions[session_ref].last_accessed = datetime.now()
        
        return self.sessions[session_ref]
    
    def _enforce_completion(
        self,
        session_state: SessionState,
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Enforce completion requirements before exit"""
        # Check if completion can be bypassed
        if CompletionEnforcement.can_bypass_completion(session_state, payload):
            return {"success": True, "message": "Completion bypassed for force exit"}
        
        # Validate completion requirements
        is_satisfied, decline = CompletionEnforcement.validate_completion_requirements(
            session_state, payload
        )
        
        if not is_satisfied:
            return {
                "success": False,
                "message": decline.message if decline else "Completion requirements not met"
            }
        
        # Update room state
        self.room_state.completion_enforced = True
        
        return {"success": True, "message": "Completion requirements satisfied"}
    
    def _capture_diagnostics(
        self,
        session_state: SessionState,
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Capture exit diagnostics"""
        # Determine exit reason
        exit_reason = ExitReason.NORMAL_COMPLETION
        if payload and "exit_reason" in payload:
            try:
                exit_reason = ExitReason(payload["exit_reason"])
            except ValueError:
                exit_reason = ExitReason.ERROR_CONDITION
        
        # Capture diagnostics
        diagnostics = ExitDiagnosticsCapture.capture_exit_diagnostics(
            session_state, exit_reason, payload
        )
        
        # Validate diagnostics
        is_valid, decline = ExitDiagnosticsCapture.validate_diagnostics_capture(diagnostics)
        if not is_valid:
            return {
                "success": False,
                "message": decline.message if decline else "Diagnostics capture failed"
            }
        
        # Update room state
        self.room_state.diagnostics_captured = True
        self.room_state.exit_diagnostics = diagnostics
        
        return {
            "success": True,
            "message": "Diagnostics captured successfully",
            "diagnostics": diagnostics
        }
    
    def _commit_to_memory(
        self,
        session_state: SessionState,
        diagnostics: ExitDiagnostics,
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Commit exit data to memory"""
        # Prepare memory commit data
        commit_data = MemoryCommit.prepare_memory_commit(
            session_state, diagnostics, payload
        )
        
        # Validate commit data
        is_valid, decline = MemoryCommit.validate_memory_commit(commit_data)
        if not is_valid:
            return {
                "success": False,
                "message": decline.message if decline else "Memory commit validation failed"
            }
        
        # Execute memory commit
        success, error_message = MemoryCommit.execute_memory_commit(commit_data)
        if not success:
            return {
                "success": False,
                "message": f"Memory commit failed: {error_message}"
            }
        
        # Update room state
        self.room_state.memory_committed = True
        
        return {
            "success": True,
            "message": "Memory commit successful",
            "commit_data": commit_data
        }
    
    def _reset_session_state(
        self,
        session_state: SessionState,
        diagnostics: ExitDiagnostics
    ) -> Dict[str, Any]:
        """Reset session state for clean re-entry"""
        # Execute state reset
        success, error_message = StateReset.reset_session_state(session_state, diagnostics)
        if not success:
            return {
                "success": False,
                "message": f"State reset failed: {error_message}"
            }
        
        # Validate reset
        is_valid, decline = StateReset.validate_state_reset(session_state, diagnostics)
        if not is_valid:
            return {
                "success": False,
                "message": decline.message if decline else "State reset validation failed"
            }
        
        # Update room state
        self.room_state.state_reset = True
        
        return {
            "success": True,
            "message": "State reset successful"
        }
    
    def _create_success_output(
        self,
        session_state: SessionState,
        diagnostics: ExitDiagnostics,
        commit_data: MemoryCommitData
    ) -> ExitRoomOutput:
        """Create successful exit output"""
        # Build display text
        display_parts = [
            "## Exit Room - Session Successfully Terminated",
            "",
            CompletionEnforcement.format_completion_summary(
                session_state, True, {"completion_confirmed": True}
            ),
            "",
            ExitDiagnosticsCapture.format_diagnostics_summary(diagnostics),
            "",
            MemoryCommit.format_memory_commit_summary(commit_data),
            "",
            StateReset.format_reset_summary(session_state, diagnostics),
            "",
            "## Exit Room Status",
            "✅ Completion requirements enforced",
            "✅ Exit diagnostics captured",
            "✅ Final state committed to memory",
            "✅ Session state reset for clean re-entry",
            "",
            "**Session terminated successfully** - Ready for new session entry."
        ]
        
        display_text = "\n".join(display_parts)
        
        return ExitRoomOutput(
            display_text=display_text,
            next_action="continue"
        )
    
    def _create_error_output(self, message: str) -> ExitRoomOutput:
        """Create error output"""
        error_parts = [
            "## Exit Room - Session Termination Failed",
            "",
            f"**Error**: {message}",
            "",
            "**Exit Room Status**:",
            f"❌ Completion Enforced: {'Yes' if self.room_state.completion_enforced else 'No'}",
            f"❌ Diagnostics Captured: {'Yes' if self.room_state.diagnostics_captured else 'No'}",
            f"❌ Memory Committed: {'Yes' if self.room_state.memory_committed else 'No'}",
            f"❌ State Reset: {'Yes' if self.room_state.state_reset else 'No'}",
            "",
            "**Action Required**: Please resolve the error and retry session termination.",
            "",
            "**Note**: Session state remains unchanged until successful exit."
        ]
        
        display_text = "\n".join(error_parts)
        
        return ExitRoomOutput(
            display_text=display_text,
            next_action="continue"
        )
    
    def get_room_status(self) -> Dict[str, Any]:
        """Get current room status"""
        return {
            "room_id": "exit_room",
            "completion_enforced": self.room_state.completion_enforced,
            "diagnostics_captured": self.room_state.diagnostics_captured,
            "memory_committed": self.room_state.memory_committed,
            "state_reset": self.room_state.state_reset,
            "active_sessions": len([s for s in self.sessions.values() if s.is_active]),
            "total_sessions": len(self.sessions),
            "errors": self.room_state.errors
        }
    
    def get_session_status(self, session_ref: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific session"""
        if session_ref not in self.sessions:
            return None
        
        session = self.sessions[session_ref]
        return {
            "session_id": session.session_id,
            "is_active": session.is_active,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "last_accessed": session.last_accessed.isoformat() if session.last_accessed else None,
            "completion_required": session.completion_required,
            "diagnostics_enabled": session.diagnostics_enabled,
            "temporary_buffers_count": len(session.temporary_buffers),
            "session_data_count": len(session.session_data)
        }


def run_exit_room(input_data: Union[ExitRoomInput, Dict[str, Any]]) -> Dict[str, Any]:
    """Convenience function to run the Exit Room"""
    from rooms.exit_room.contract_types import ExitRoomInput
    from dataclasses import asdict
    inp = ExitRoomInput.from_obj(input_data)
    room = ExitRoom()
    result = room.process_exit(inp)
    return asdict(result)
