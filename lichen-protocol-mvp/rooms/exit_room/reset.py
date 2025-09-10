from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from .contract_types import (
    ExitReason, ExitDiagnostics, SessionState, 
    DeclineReason, DeclineResponse, ExitOperationResult
)


class StateReset:
    """Handles session state reset for clean re-entry"""
    
    @staticmethod
    def reset_session_state(
        session_state: SessionState,
        exit_diagnostics: ExitDiagnostics
    ) -> Tuple[bool, Optional[str]]:
        """
        Reset session state for clean re-entry.
        Returns: (success, error_message)
        """
        try:
            # Mark session as inactive
            session_state.is_active = False
            
            # Clear temporary buffers
            StateReset._clear_temporary_buffers(session_state)
            
            # Clear session data
            StateReset._clear_session_data(session_state)
            
            # Update last accessed timestamp
            session_state.last_accessed = datetime.now()
            
            # Update diagnostics to reflect successful reset
            exit_diagnostics.state_reset = True
            
            return True, None
            
        except Exception as e:
            return False, f"State reset exception: {str(e)}"
    
    @staticmethod
    def validate_state_reset(
        session_state: SessionState,
        exit_diagnostics: ExitDiagnostics
    ) -> Tuple[bool, Optional[DeclineResponse]]:
        """
        Validate that state reset was successful.
        Returns: (is_valid, decline_response)
        """
        # Check if session is marked as inactive
        if session_state.is_active:
            decline = DeclineResponse(
                reason=DeclineReason.STATE_RESET_FAILED,
                message="State reset failed: session still marked as active",
                details="Session must be marked as inactive after reset",
                required_fields=["is_active"]
            )
            return False, decline
        
        # Check if temporary buffers are cleared
        if session_state.temporary_buffers:
            decline = DeclineResponse(
                reason=DeclineReason.STATE_RESET_FAILED,
                message="State reset failed: temporary buffers not cleared",
                details="All temporary buffers must be cleared",
                required_fields=["temporary_buffers"]
            )
            return False, decline
        
        # Check if session data is cleared
        if session_state.session_data:
            decline = DeclineResponse(
                reason=DeclineReason.STATE_RESET_FAILED,
                message="State reset failed: session data not cleared",
                details="All session data must be cleared",
                required_fields=["session_data"]
            )
            return False, decline
        
        # Check if reset flag is set in diagnostics
        if not exit_diagnostics.state_reset:
            decline = DeclineResponse(
                reason=DeclineReason.STATE_RESET_FAILED,
                message="State reset failed: reset flag not set in diagnostics",
                details="State reset flag must be set in diagnostics",
                required_fields=["diagnostics.state_reset"]
            )
            return False, decline
        
        return True, None
    
    @staticmethod
    def format_reset_summary(
        session_state: SessionState,
        exit_diagnostics: ExitDiagnostics
    ) -> str:
        """Format state reset summary for display"""
        summary_parts = [
            "## Exit Room - State Reset Summary",
            f"**Session ID**: {session_state.session_id}",
            f"**Session Active**: {'❌ No' if not session_state.is_active else '⚠️ Yes (Reset Failed)'}",
            f"**Temporary Buffers**: {'✅ Cleared' if not session_state.temporary_buffers else '❌ Not Cleared'}",
            f"**Session Data**: {'✅ Cleared' if not session_state.session_data else '❌ Not Cleared'}",
            f"**State Reset Flag**: {'✅ Set' if exit_diagnostics.state_reset else '❌ Not Set'}",
            ""
        ]
        
        if session_state.last_accessed:
            summary_parts.append(f"**Last Accessed**: {session_state.last_accessed.strftime('%Y-%m-%d %H:%M:%S')}")
        
        summary_parts.extend([
            "",
            "**Reset Status**: ✅ Session state successfully reset for clean re-entry"
        ])
        
        return "\n".join(summary_parts)
    
    @staticmethod
    def get_reset_requirements() -> List[str]:
        """Get list of required reset operations"""
        return [
            "mark_session_inactive",
            "clear_temporary_buffers",
            "clear_session_data",
            "update_timestamp",
            "set_reset_flag"
        ]
    
    @staticmethod
    def _clear_temporary_buffers(session_state: SessionState) -> None:
        """Clear all temporary buffers"""
        session_state.temporary_buffers.clear()
    
    @staticmethod
    def _clear_session_data(session_state: SessionState) -> None:
        """Clear all session data"""
        session_state.session_data.clear()
    
    @staticmethod
    def can_reenter_session(session_state: SessionState) -> bool:
        """Check if session can be re-entered after reset"""
        # Session can be re-entered if it's inactive and buffers are cleared
        return (not session_state.is_active and 
                not session_state.temporary_buffers and 
                not session_state.session_data)
    
    @staticmethod
    def prepare_for_reentry(session_state: SessionState) -> bool:
        """Prepare session state for potential re-entry"""
        try:
            # Reset completion and diagnostics flags
            session_state.completion_required = True
            session_state.diagnostics_enabled = True
            
            # Clear any remaining state
            if hasattr(session_state, 'errors'):
                session_state.errors.clear()
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_reset_consistency(
        session_state: SessionState,
        exit_diagnostics: ExitDiagnostics
    ) -> Tuple[bool, Optional[str]]:
        """
        Ensure state reset is consistent across all components.
        Returns: (is_consistent, inconsistency_reason)
        """
        # Check session state consistency
        if session_state.is_active:
            return False, "Session still marked as active after reset"
        
        if session_state.temporary_buffers:
            return False, "Temporary buffers not cleared after reset"
        
        if session_state.session_data:
            return False, "Session data not cleared after reset"
        
        # Check diagnostics consistency
        if not exit_diagnostics.state_reset:
            return False, "State reset flag not set in diagnostics"
        
        # Check timestamp consistency
        if not session_state.last_accessed:
            return False, "Last accessed timestamp not updated after reset"
        
        return True, None
    
    @staticmethod
    def create_reset_result(
        success: bool,
        session_state: SessionState,
        exit_diagnostics: ExitDiagnostics,
        error_message: Optional[str] = None
    ) -> ExitOperationResult:
        """Create operation result for state reset"""
        if success:
            return ExitOperationResult(
                success=True,
                message="State reset successful",
                diagnostics=exit_diagnostics,
                memory_commit_result=exit_diagnostics.memory_committed,
                state_reset_result=True
            )
        else:
            return ExitOperationResult(
                success=False,
                message="State reset failed",
                diagnostics=exit_diagnostics,
                memory_commit_result=exit_diagnostics.memory_committed,
                state_reset_result=False,
                error_details=error_message
            )
    
    @staticmethod
    def get_reset_statistics(session_state: SessionState) -> Dict[str, Any]:
        """Get statistics about the reset operation"""
        return {
            "session_id": session_state.session_id,
            "is_active": session_state.is_active,
            "temporary_buffers_cleared": len(session_state.temporary_buffers) == 0,
            "session_data_cleared": len(session_state.session_data) == 0,
            "last_accessed": session_state.last_accessed.isoformat() if session_state.last_accessed else None,
            "completion_required": session_state.completion_required,
            "diagnostics_enabled": session_state.diagnostics_enabled,
            "reset_timestamp": datetime.now().isoformat()
        }
