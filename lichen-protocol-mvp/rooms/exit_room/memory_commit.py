from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from .contract_types import (
    ExitReason, ExitDiagnostics, MemoryCommitData, SessionState,
    DeclineReason, DeclineResponse, ExitOperationResult
)


class MemoryCommit:
    """Handles atomic commit of exit data to memory"""
    
    @staticmethod
    def prepare_memory_commit(
        session_state: SessionState,
        exit_diagnostics: ExitDiagnostics,
        payload: Optional[Dict[str, Any]] = None
    ) -> MemoryCommitData:
        """
        Prepare data for memory commit.
        Returns structured data ready for atomic write.
        """
        # Create final state snapshot
        final_state_snapshot = MemoryCommit._create_final_state_snapshot(
            session_state, exit_diagnostics, payload
        )
        
        # Create memory commit data
        commit_data = MemoryCommitData(
            session_id=session_state.session_id,
            exit_reason=exit_diagnostics.exit_reason,
            diagnostics=exit_diagnostics,
            closure_flag=True,  # Always set closure flag
            final_state_snapshot=final_state_snapshot,
            timestamp=datetime.now()
        )
        
        return commit_data
    
    @staticmethod
    def execute_memory_commit(
        commit_data: MemoryCommitData
    ) -> Tuple[bool, Optional[str]]:
        """
        Execute atomic memory commit.
        Returns: (success, error_message)
        """
        try:
            # Simulate atomic memory write
            # In production, this would interface with the Memory Room
            success = MemoryCommit._write_to_memory(commit_data)
            
            if not success:
                return False, "Memory write operation failed"
            
            # Update diagnostics to reflect successful commit
            commit_data.diagnostics.memory_committed = True
            
            return True, None
            
        except Exception as e:
            return False, f"Memory commit exception: {str(e)}"
    
    @staticmethod
    def validate_memory_commit(
        commit_data: MemoryCommitData
    ) -> Tuple[bool, Optional[DeclineResponse]]:
        """
        Validate memory commit data before writing.
        Returns: (is_valid, decline_response)
        """
        # Check required fields
        if not commit_data.session_id:
            decline = DeclineResponse(
                reason=DeclineReason.MEMORY_COMMIT_FAILED,
                message="Memory commit failed: missing session ID",
                details="Session ID is required for memory commit",
                required_fields=["session_id"]
            )
            return False, decline
        
        if not commit_data.exit_reason:
            decline = DeclineResponse(
                reason=DeclineReason.MEMORY_COMMIT_FAILED,
                message="Memory commit failed: missing exit reason",
                details="Exit reason is required for memory commit",
                required_fields=["exit_reason"]
            )
            return False, decline
        
        if not commit_data.diagnostics:
            decline = DeclineResponse(
                reason=DeclineReason.MEMORY_COMMIT_FAILED,
                message="Memory commit failed: missing diagnostics",
                details="Exit diagnostics are required for memory commit",
                required_fields=["diagnostics"]
            )
            return False, decline
        
        # Validate diagnostics structure
        if not commit_data.diagnostics.diagnostics_captured:
            decline = DeclineResponse(
                reason=DeclineReason.MEMORY_COMMIT_FAILED,
                message="Memory commit failed: diagnostics not captured",
                details="Diagnostics must be captured before memory commit",
                required_fields=["diagnostics.diagnostics_captured"]
            )
            return False, decline
        
        return True, None
    
    @staticmethod
    def format_memory_commit_summary(commit_data: MemoryCommitData) -> str:
        """Format memory commit summary for display"""
        summary_parts = [
            "## Exit Room - Memory Commit Summary",
            f"**Session ID**: {commit_data.session_id}",
            f"**Exit Reason**: {commit_data.exit_reason.value}",
            f"**Closure Flag**: {'✅ Set' if commit_data.closure_flag else '❌ Not Set'}",
            f"**Diagnostics Captured**: {'✅ Yes' if commit_data.diagnostics.diagnostics_captured else '❌ No'}",
            f"**Memory Committed**: {'✅ Yes' if commit_data.diagnostics.memory_committed else '❌ No'}",
            f"**State Reset**: {'✅ Yes' if commit_data.diagnostics.state_reset else '❌ No'}",
            ""
        ]
        
        if commit_data.final_state_snapshot:
            summary_parts.extend([
                "**Final State Snapshot**:",
                f"- Session Active: {'Yes' if commit_data.final_state_snapshot.get('is_active') else 'No'}",
                f"- Completion Required: {'Yes' if commit_data.final_state_snapshot.get('completion_required') else 'No'}",
                f"- Diagnostics Enabled: {'Yes' if commit_data.final_state_snapshot.get('diagnostics_enabled') else 'No'}",
                f"- Temporary Buffers: {commit_data.final_state_snapshot.get('temporary_buffers_count', 0)}",
                f"- Session Data Items: {commit_data.final_state_snapshot.get('session_data_count', 0)}",
                ""
            ])
        
        summary_parts.extend([
            f"**Commit Timestamp**: {commit_data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "**Memory Commit Status**: ✅ Successfully committed to memory"
        ])
        
        return "\n".join(summary_parts)
    
    @staticmethod
    def get_memory_commit_requirements() -> List[str]:
        """Get list of required memory commit fields"""
        return [
            "session_id",
            "exit_reason",
            "diagnostics",
            "closure_flag",
            "timestamp"
        ]
    
    @staticmethod
    def _create_final_state_snapshot(
        session_state: SessionState,
        exit_diagnostics: ExitDiagnostics,
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create final state snapshot for memory commit"""
        snapshot = {
            "session_id": session_state.session_id,
            "is_active": session_state.is_active,
            "completion_required": session_state.completion_required,
            "diagnostics_enabled": session_state.diagnostics_enabled,
            "temporary_buffers_count": len(session_state.temporary_buffers),
            "session_data_count": len(session_state.session_data),
            "exit_timestamp": datetime.now().isoformat(),
            "exit_reason": exit_diagnostics.exit_reason.value,
            "completion_satisfied": exit_diagnostics.completion_satisfied,
            "session_duration": exit_diagnostics.session_duration
        }
        
        # Add buffer information
        if session_state.temporary_buffers:
            snapshot["buffer_types"] = list(session_state.temporary_buffers.keys())
        
        # Add session data types
        if session_state.session_data:
            snapshot["data_types"] = list(session_state.session_data.keys())
        
        # Add payload context
        if payload:
            snapshot["exit_payload_keys"] = list(payload.keys())
            snapshot["force_exit"] = payload.get("force_exit", False)
            snapshot["completion_quality"] = payload.get("completion_quality", "basic")
        
        return snapshot
    
    @staticmethod
    def _write_to_memory(commit_data: MemoryCommitData) -> bool:
        """
        Simulate writing to memory.
        In production, this would interface with the Memory Room.
        """
        # Simulate memory write operation
        # This is a deterministic simulation - no heuristics
        try:
            # Simulate successful write
            # In reality, this would call the Memory Room's interface
            return True
        except Exception:
            return False
    
    @staticmethod
    def create_memory_commit_result(
        success: bool,
        commit_data: MemoryCommitData,
        error_message: Optional[str] = None
    ) -> ExitOperationResult:
        """Create operation result for memory commit"""
        if success:
            return ExitOperationResult(
                success=True,
                message="Memory commit successful",
                diagnostics=commit_data.diagnostics,
                memory_commit_result=True,
                state_reset_result=None  # Will be set later
            )
        else:
            return ExitOperationResult(
                success=False,
                message="Memory commit failed",
                diagnostics=commit_data.diagnostics,
                memory_commit_result=False,
                error_details=error_message
            )
    
    @staticmethod
    def validate_commit_consistency(
        commit_data: MemoryCommitData,
        session_state: SessionState
    ) -> Tuple[bool, Optional[str]]:
        """
        Ensure memory commit data is consistent with session state.
        Returns: (is_consistent, inconsistency_reason)
        """
        # Check session ID consistency
        if commit_data.session_id != session_state.session_id:
            return False, "Session ID mismatch between commit data and session state"
        
        # Check exit reason consistency
        if commit_data.exit_reason not in [ExitReason.NORMAL_COMPLETION, ExitReason.ABORTED, 
                                         ExitReason.FORCE_CLOSED, ExitReason.ERROR_CONDITION]:
            return False, "Invalid exit reason in commit data"
        
        # Check diagnostics consistency
        if not commit_data.diagnostics:
            return False, "Missing diagnostics in commit data"
        
        if commit_data.diagnostics.session_id != session_state.session_id:
            return False, "Diagnostics session ID mismatch"
        
        return True, None
