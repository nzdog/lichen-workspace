from typing import List, Literal, Optional, Dict, Any, Tuple
from .contract_types import Commitment, PaceState, DeclineReason, DeclineResponse


class PaceEnforcement:
    """Enforces pace state requirements on all commitments"""
    
    @staticmethod
    def validate_pace_states(commitments: List[Commitment]) -> Tuple[bool, Optional[DeclineResponse]]:
        """
        Validate that all commitments have valid pace states.
        Returns: (is_valid, decline_response)
        """
        if not commitments:
            return False, DeclineResponse(
                reason=DeclineReason.MISSING_PACE_STATE,
                message="No commitments provided for pace validation",
                details="Commitments list is empty",
                required_fields=["commitments"]
            )
        
        # Check each commitment for pace state
        missing_pace_commitments = []
        for i, commitment in enumerate(commitments):
            if not commitment.pace_state:
                missing_pace_commitments.append(f"Commitment {i+1}")
        
        if missing_pace_commitments:
            decline = DeclineResponse(
                reason=DeclineReason.MISSING_PACE_STATE,
                message=f"Missing pace state on commitments: {', '.join(missing_pace_commitments)}",
                details="All commitments must have a pace state",
                required_fields=["pace_state"]
            )
            return False, decline
        
        # Validate pace state values
        invalid_pace_commitments = []
        for i, commitment in enumerate(commitments):
            try:
                # This should always work since we're using the enum, but double-check
                PaceState(commitment.pace_state.value)
            except (ValueError, AttributeError):
                invalid_pace_commitments.append(f"Commitment {i+1}")
        
        if invalid_pace_commitments:
            decline = DeclineResponse(
                reason=DeclineReason.MISSING_PACE_STATE,
                message=f"Invalid pace state on commitments: {', '.join(invalid_pace_commitments)}",
                details="Pace states must be valid enum values",
                required_fields=["pace_state"]
            )
            return False, decline
        
        return True, None
    
    @staticmethod
    def map_pace_to_action(pace_state: PaceState) -> Literal["continue", "hold", "later"]:
        """
        Map pace state to next_action.
        NOW → continue, HOLD/SOFT_HOLD → hold, LATER → later
        """
        if pace_state == PaceState.NOW:
            return "continue"
        elif pace_state == PaceState.LATER:
            return "later"
        else:  # HOLD or SOFT_HOLD
            return "hold"
    
    @staticmethod
    def get_room_next_action(commitments: List[Commitment]) -> Literal["continue", "hold", "later"]:
        """
        Determine the room's next_action based on commitment pace states.
        Returns the most restrictive action (LATER > HOLD > NOW).
        """
        if not commitments:
            return "continue"  # Default if no commitments
        
        # Priority order: LATER > HOLD > NOW
        pace_priorities = {
            PaceState.LATER: 3,
            PaceState.HOLD: 2,
            PaceState.SOFT_HOLD: 2,
            PaceState.NOW: 1
        }
        
        # Find the highest priority pace state
        highest_priority = 0
        highest_priority_pace = PaceState.NOW
        
        for commitment in commitments:
            priority = pace_priorities.get(commitment.pace_state, 0)
            if priority > highest_priority:
                highest_priority = priority
                highest_priority_pace = commitment.pace_state
        
        return PaceEnforcement.map_pace_to_action(highest_priority_pace)
    
    @staticmethod
    def get_pace_distribution(commitments: List[Commitment]) -> Dict[str, int]:
        """Get distribution of pace states across commitments"""
        distribution = {
            PaceState.NOW.value: 0,
            PaceState.HOLD.value: 0,
            PaceState.LATER.value: 0,
            PaceState.SOFT_HOLD.value: 0
        }
        
        for commitment in commitments:
            pace_value = commitment.pace_state.value
            distribution[pace_value] = distribution.get(pace_value, 0) + 1
        
        return distribution
    
    @staticmethod
    def validate_pace_consistency(commitments: List[Commitment]) -> Tuple[bool, Optional[str]]:
        """
        Check for potential pace consistency issues.
        Returns: (is_consistent, warning_message)
        """
        if len(commitments) < 2:
            return True, None  # No consistency issues with single commitment
        
        pace_distribution = PaceEnforcement.get_pace_distribution(commitments)
        
        # Check for extreme imbalances
        total_commitments = len(commitments)
        now_count = pace_distribution[PaceState.NOW.value]
        later_count = pace_distribution[PaceState.LATER.value]
        
        # Warning if all commitments are NOW (potential urgency drift)
        if now_count == total_commitments and total_commitments > 1:
            return True, "All commitments marked as NOW - consider if some could be HOLD or LATER"
        
        # Warning if all commitments are LATER (potential procrastination)
        if later_count == total_commitments and total_commitments > 1:
            return True, "All commitments marked as LATER - consider if some could be NOW or HOLD"
        
        return True, None
    
    @staticmethod
    def get_pace_guidance(pace_state: PaceState) -> str:
        """Get human-readable guidance for a pace state"""
        guidance = {
            PaceState.NOW: "Ready to proceed immediately",
            PaceState.HOLD: "Pause here until ready to continue",
            PaceState.LATER: "Schedule for later session",
            PaceState.SOFT_HOLD: "Brief pause, can continue when ready"
        }
        return guidance.get(pace_state, "Unknown pace state")
    
    @staticmethod
    def format_pace_summary(commitments: List[Commitment]) -> str:
        """Format pace information into a human-readable summary"""
        if not commitments:
            return "**No pace information available**"
        
        pace_distribution = PaceEnforcement.get_pace_distribution(commitments)
        next_action = PaceEnforcement.get_room_next_action(commitments)
        
        summary_parts = [
            "## Pace Summary",
            f"**Room Next Action**: {next_action}",
            "",
            "**Pace Distribution**:"
        ]
        
        for pace_value, count in pace_distribution.items():
            if count > 0:
                guidance = PaceEnforcement.get_pace_guidance(PaceState(pace_value))
                summary_parts.append(f"- **{pace_value}**: {count} commitment(s) - {guidance}")
        
        # Add consistency warning if any
        is_consistent, warning = PaceEnforcement.validate_pace_consistency(commitments)
        if warning:
            summary_parts.extend([
                "",
                "**Pace Guidance**:",
                f"⚠️ {warning}"
            ])
        
        return "\n".join(summary_parts)
    
    @staticmethod
    def get_required_pace_states() -> List[str]:
        """Get list of valid pace state values"""
        return [state.value for state in PaceState]
    
    @staticmethod
    def is_pace_state_valid(pace_value: str) -> bool:
        """Check if a pace state value is valid"""
        try:
            PaceState(pace_value)
            return True
        except ValueError:
            return False
