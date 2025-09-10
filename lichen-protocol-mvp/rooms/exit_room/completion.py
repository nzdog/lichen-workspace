from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from .contract_types import (
    ExitReason, DeclineReason, DeclineResponse, 
    ExitDiagnostics, SessionState
)


class CompletionEnforcement:
    """Enforces completion prompts before allowing session termination"""
    
    @staticmethod
    def validate_completion_requirements(
        session_state: SessionState,
        payload: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[DeclineResponse]]:
        """
        Validate that completion requirements are satisfied.
        Returns: (is_satisfied, decline_response)
        """
        # Check if completion is required for this session
        if not session_state.completion_required:
            return True, None
        
        # Check if payload contains completion confirmation
        if not payload:
            decline = DeclineResponse(
                reason=DeclineReason.COMPLETION_NOT_SATISFIED,
                message="Completion confirmation required before session termination",
                details="Payload must contain completion confirmation",
                required_fields=["completion_confirmed"]
            )
            return False, decline
        
        # Validate completion confirmation
        completion_confirmed = payload.get("completion_confirmed")
        if not completion_confirmed:
            decline = DeclineResponse(
                reason=DeclineReason.COMPLETION_NOT_SATISFIED,
                message="Completion confirmation must be explicitly provided",
                details="completion_confirmed must be true to proceed",
                required_fields=["completion_confirmed"]
            )
            return False, decline
        
        # Check for required completion fields if specified
        required_fields = payload.get("required_completion_fields", [])
        if required_fields:
            missing_fields = []
            for field in required_fields:
                if field not in payload or not payload[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                decline = DeclineResponse(
                    reason=DeclineReason.COMPLETION_NOT_SATISFIED,
                    message=f"Missing required completion fields: {', '.join(missing_fields)}",
                    details="All required completion fields must be provided",
                    required_fields=missing_fields
                )
                return False, decline
        
        # Check for completion quality indicators
        completion_quality = payload.get("completion_quality", "basic")
        if completion_quality == "basic":
            # Basic completion requires minimal confirmation
            if not payload.get("session_goals_met", False):
                decline = DeclineResponse(
                    reason=DeclineReason.COMPLETION_NOT_SATISFIED,
                    message="Basic completion requires session goals confirmation",
                    details="session_goals_met must be true for basic completion",
                    required_fields=["session_goals_met"]
                )
                return False, decline
        
        elif completion_quality == "comprehensive":
            # Comprehensive completion requires more validation
            required_comprehensive_fields = [
                "session_goals_met",
                "integration_complete",
                "commitments_recorded",
                "reflection_done"
            ]
            
            missing_comprehensive = []
            for field in required_comprehensive_fields:
                if not payload.get(field, False):
                    missing_comprehensive.append(field)
            
            if missing_comprehensive:
                decline = DeclineResponse(
                    reason=DeclineReason.COMPLETION_NOT_SATISFIED,
                    message=f"Comprehensive completion missing: {', '.join(missing_comprehensive)}",
                    details="All comprehensive completion fields must be true",
                    required_fields=missing_comprehensive
                )
                return False, decline
        
        return True, None
    
    @staticmethod
    def create_completion_diagnostics(
        session_state: SessionState,
        completion_satisfied: bool,
        payload: Optional[Dict[str, Any]] = None
    ) -> ExitDiagnostics:
        """Create completion diagnostics for the exit process"""
        return ExitDiagnostics(
            session_id=session_state.session_id,
            exit_reason=ExitReason.NORMAL_COMPLETION,
            completion_satisfied=completion_satisfied,
            diagnostics_captured=False,  # Will be set later
            memory_committed=False,      # Will be set later
            state_reset=False,           # Will be set later
            session_duration=CompletionEnforcement._calculate_session_duration(session_state),
            error_summary=None
        )
    
    @staticmethod
    def format_completion_summary(
        session_state: SessionState,
        completion_satisfied: bool,
        payload: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format completion summary for display"""
        summary_parts = [
            "## Exit Room - Completion Summary",
            f"**Session ID**: {session_state.session_id}",
            f"**Completion Required**: {'Yes' if session_state.completion_required else 'No'}",
            f"**Completion Satisfied**: {'✅ Yes' if completion_satisfied else '❌ No'}",
            ""
        ]
        
        if completion_satisfied and payload:
            summary_parts.extend([
                "**Completion Details**:",
                f"- Goals Met: {'✅' if payload.get('session_goals_met') else '❌'}",
                f"- Integration Complete: {'✅' if payload.get('integration_complete') else '❌'}",
                f"- Commitments Recorded: {'✅' if payload.get('commitments_recorded') else '❌'}",
                f"- Reflection Done: {'✅' if payload.get('reflection_done') else '❌'}",
                ""
            ])
        
        if session_state.completion_required and not completion_satisfied:
            summary_parts.extend([
                "**Completion Requirements Not Met**:",
                "Session cannot terminate until completion is confirmed.",
                "Please provide completion confirmation in the payload.",
                ""
            ])
        
        summary_parts.append(f"**Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(summary_parts)
    
    @staticmethod
    def get_completion_requirements() -> List[str]:
        """Get list of required completion fields"""
        return [
            "completion_confirmed",
            "session_goals_met",
            "integration_complete",
            "commitments_recorded",
            "reflection_done"
        ]
    
    @staticmethod
    def validate_completion_payload_structure(payload: Dict[str, Any]) -> bool:
        """Validate the structure of completion payload"""
        if not isinstance(payload, dict):
            return False
        
        # Check for required base field
        if "completion_confirmed" not in payload:
            return False
        
        # Check that completion_confirmed is boolean
        if not isinstance(payload["completion_confirmed"], bool):
            return False
        
        return True
    
    @staticmethod
    def _calculate_session_duration(session_state: SessionState) -> Optional[float]:
        """Calculate session duration in seconds"""
        if not session_state.created_at:
            return None
        
        duration = datetime.now() - session_state.created_at
        return duration.total_seconds()
    
    @staticmethod
    def can_bypass_completion(session_state: SessionState, payload: Optional[Dict[str, Any]] = None) -> bool:
        """Check if completion can be bypassed (for force-closed sessions)"""
        if not payload:
            return False
        
        # Only allow bypass for force-closed or aborted sessions
        exit_reason = payload.get("exit_reason")
        if exit_reason in ["force_closed", "aborted", "error_condition"]:
            return True
        
        return False
    
    @staticmethod
    def enforce_completion_consistency(
        session_state: SessionState,
        payload: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Ensure completion requirements are consistent across the session.
        Returns: (is_consistent, inconsistency_reason)
        """
        if not session_state.completion_required:
            return True, None
        
        # Check for completion consistency indicators
        if payload and "completion_consistency_check" in payload:
            consistency_check = payload["completion_consistency_check"]
            
            if not isinstance(consistency_check, dict):
                return False, "Completion consistency check must be a dictionary"
            
            required_checks = ["session_state_valid", "goals_aligned", "no_pending_actions"]
            for check in required_checks:
                if check not in consistency_check or not consistency_check[check]:
                    return False, f"Completion consistency check failed: {check}"
        
        return True, None
