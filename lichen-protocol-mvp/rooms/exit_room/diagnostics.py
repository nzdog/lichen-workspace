from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from .contract_types import (
    ExitReason, ExitDiagnostics, SessionState, 
    DeclineReason, DeclineResponse
)


class ExitDiagnosticsCapture:
    """Captures final session diagnostics at exit"""
    
    @staticmethod
    def capture_exit_diagnostics(
        session_state: SessionState,
        exit_reason: ExitReason,
        payload: Optional[Dict[str, Any]] = None
    ) -> ExitDiagnostics:
        """
        Capture comprehensive exit diagnostics.
        Returns structured diagnostics for memory commit.
        """
        # Determine exit reason from payload or default
        if payload and "exit_reason" in payload:
            try:
                exit_reason = ExitReason(payload["exit_reason"])
            except ValueError:
                exit_reason = ExitReason.ERROR_CONDITION
        
        # Calculate session duration
        session_duration = ExitDiagnosticsCapture._calculate_session_duration(session_state)
        
        # Capture error summary if any
        error_summary = ExitDiagnosticsCapture._capture_error_summary(session_state, payload)
        
        # Create diagnostics object
        diagnostics = ExitDiagnostics(
            session_id=session_state.session_id,
            exit_reason=exit_reason,
            completion_satisfied=ExitDiagnosticsCapture._check_completion_satisfied(payload),
            diagnostics_captured=True,  # This will be set to true
            memory_committed=False,     # Will be set later
            state_reset=False,          # Will be set later
            final_timestamp=datetime.now(),
            session_duration=session_duration,
            error_summary=error_summary
        )
        
        return diagnostics
    
    @staticmethod
    def validate_diagnostics_capture(
        diagnostics: ExitDiagnostics
    ) -> Tuple[bool, Optional[DeclineResponse]]:
        """
        Validate that diagnostics capture was successful.
        Returns: (is_valid, decline_response)
        """
        # Check required fields
        if not diagnostics.session_id:
            decline = DeclineResponse(
                reason=DeclineReason.DIAGNOSTICS_FAILED,
                message="Diagnostics capture failed: missing session ID",
                details="Session ID is required for diagnostics",
                required_fields=["session_id"]
            )
            return False, decline
        
        if not diagnostics.exit_reason:
            decline = DeclineResponse(
                reason=DeclineReason.DIAGNOSTICS_FAILED,
                message="Diagnostics capture failed: missing exit reason",
                details="Exit reason is required for diagnostics",
                required_fields=["exit_reason"]
            )
            return False, decline
        
        if not diagnostics.diagnostics_captured:
            decline = DeclineResponse(
                reason=DeclineReason.DIAGNOSTICS_FAILED,
                message="Diagnostics capture failed: capture flag not set",
                details="Diagnostics must be marked as captured",
                required_fields=["diagnostics_captured"]
            )
            return False, decline
        
        return True, None
    
    @staticmethod
    def format_diagnostics_summary(diagnostics: ExitDiagnostics) -> str:
        """Format diagnostics into human-readable summary"""
        summary_parts = [
            "## Exit Room - Diagnostics Summary",
            f"**Session ID**: {diagnostics.session_id}",
            f"**Exit Reason**: {diagnostics.exit_reason.value}",
            f"**Completion Satisfied**: {'✅ Yes' if diagnostics.completion_satisfied else '❌ No'}",
            f"**Diagnostics Captured**: {'✅ Yes' if diagnostics.diagnostics_captured else '❌ No'}",
            f"**Memory Committed**: {'✅ Yes' if diagnostics.memory_committed else '❌ No'}",
            f"**State Reset**: {'✅ Yes' if diagnostics.state_reset else '❌ No'}",
            ""
        ]
        
        if diagnostics.session_duration:
            summary_parts.append(f"**Session Duration**: {diagnostics.session_duration:.2f} seconds")
        
        if diagnostics.error_summary:
            summary_parts.extend([
                "",
                "**Error Summary**:",
                diagnostics.error_summary
            ])
        
        summary_parts.extend([
            "",
            f"**Final Timestamp**: {diagnostics.final_timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        ])
        
        return "\n".join(summary_parts)
    
    @staticmethod
    def capture_session_metrics(session_state: SessionState) -> Dict[str, Any]:
        """Capture session metrics for diagnostics"""
        metrics = {
            "session_id": session_state.session_id,
            "is_active": session_state.is_active,
            "created_at": session_state.created_at.isoformat() if session_state.created_at else None,
            "last_accessed": session_state.last_accessed.isoformat() if session_state.last_accessed else None,
            "completion_required": session_state.completion_required,
            "diagnostics_enabled": session_state.diagnostics_enabled,
            "temporary_buffers_count": len(session_state.temporary_buffers),
            "session_data_count": len(session_state.session_data)
        }
        
        # Add buffer information
        if session_state.temporary_buffers:
            metrics["buffer_types"] = list(session_state.temporary_buffers.keys())
        
        # Add session data types
        if session_state.session_data:
            metrics["data_types"] = list(session_state.session_data.keys())
        
        return metrics
    
    @staticmethod
    def capture_exit_context(
        session_state: SessionState,
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Capture exit context information"""
        context = {
            "exit_timestamp": datetime.now().isoformat(),
            "session_state": ExitDiagnosticsCapture.capture_session_metrics(session_state),
            "exit_payload_keys": list(payload.keys()) if payload else [],
            "exit_environment": {
                "python_version": "3.11",
                "room_id": "exit_room",
                "protocol_version": "0.1.0"
            }
        }
        
        # Add payload context if available
        if payload:
            context["exit_reason"] = payload.get("exit_reason", "unspecified")
            context["completion_quality"] = payload.get("completion_quality", "basic")
            context["force_exit"] = payload.get("force_exit", False)
        
        return context
    
    @staticmethod
    def _calculate_session_duration(session_state: SessionState) -> Optional[float]:
        """Calculate session duration in seconds"""
        if not session_state.created_at:
            return None
        
        duration = datetime.now() - session_state.created_at
        return duration.total_seconds()
    
    @staticmethod
    def _capture_error_summary(
        session_state: SessionState,
        payload: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Capture error summary if any errors occurred"""
        errors = []
        
        # Check for errors in session state
        if hasattr(session_state, 'errors') and session_state.errors:
            errors.extend(session_state.errors)
        
        # Check for errors in payload
        if payload and "errors" in payload:
            payload_errors = payload["errors"]
            if isinstance(payload_errors, list):
                errors.extend(payload_errors)
            elif isinstance(payload_errors, str):
                errors.append(payload_errors)
        
        # Check for error indicators
        if payload and payload.get("has_errors", False):
            errors.append("Session indicated presence of errors")
        
        if not errors:
            return None
        
        return "; ".join(errors)
    
    @staticmethod
    def _check_completion_satisfied(payload: Optional[Dict[str, Any]] = None) -> bool:
        """Check if completion requirements were satisfied"""
        if not payload:
            return False
        
        # Check basic completion
        if payload.get("completion_confirmed", False):
            return True
        
        # Check for force exit scenarios
        if payload.get("force_exit", False):
            return True
        
        # Check for error conditions that bypass completion
        if payload.get("exit_reason") in ["error_condition", "aborted"]:
            return True
        
        return False
    
    @staticmethod
    def get_diagnostics_requirements() -> List[str]:
        """Get list of required diagnostics fields"""
        return [
            "session_id",
            "exit_reason", 
            "completion_satisfied",
            "diagnostics_captured",
            "final_timestamp"
        ]
    
    @staticmethod
    def validate_diagnostics_structure(diagnostics: ExitDiagnostics) -> bool:
        """Validate the structure of diagnostics object"""
        required_fields = ExitDiagnosticsCapture.get_diagnostics_requirements()
        
        for field in required_fields:
            if not hasattr(diagnostics, field) or getattr(diagnostics, field) is None:
                return False
        
        return True
