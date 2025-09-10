"""
Pacing Module
Deterministic pace engine for walk steps with next_action mapping
"""

from typing import Literal, Optional, List
from .contract_types import PaceState


class PaceGovernor:
    """Governs pacing for walk steps with deterministic next_action mapping"""
    
    @staticmethod
    def validate_pace_state(pace: str) -> bool:
        """Validate that a pace state is valid"""
        valid_paces = [p.value for p in PaceState]
        return pace in valid_paces
    
    @staticmethod
    def map_pace_to_action(pace: str) -> Literal["continue", "hold", "later"]:
        """
        Deterministic mapping from pace to next_action
        NOW → continue, HOLD/SOFT_HOLD → hold, LATER → later
        """
        if not PaceGovernor.validate_pace_state(pace):
            # Default to hold for invalid pace states
            return "hold"
        
        if pace == PaceState.NOW.value:
            return "continue"
        elif pace == PaceState.LATER.value:
            return "later"
        else:  # HOLD or SOFT_HOLD
            return "hold"
    
    @staticmethod
    def can_advance_with_pace(pace: str) -> bool:
        """Check if current pace allows advancing to next step"""
        return pace == PaceState.NOW.value
    
    @staticmethod
    def get_pace_description(pace: str) -> str:
        """Get human-readable description of pace state"""
        pace_descriptions = {
            PaceState.NOW.value: "Ready to proceed immediately",
            PaceState.HOLD.value: "Pause here until ready to continue",
            PaceState.LATER.value: "Schedule for later session",
            PaceState.SOFT_HOLD.value: "Brief pause, can continue when ready"
        }
        return pace_descriptions.get(pace, "Unknown pace state")
    
    @staticmethod
    def get_pace_guidance(pace: str) -> str:
        """Get guidance text for the current pace state"""
        guidance = {
            PaceState.NOW.value: "You can proceed to the next step.",
            PaceState.HOLD.value: "Take time to process this step before continuing.",
            PaceState.LATER.value: "This step will be available in your next session.",
            PaceState.SOFT_HOLD.value: "Take a moment, then continue when ready."
        }
        return guidance.get(pace, "Please select a valid pace.")
    
    @staticmethod
    def is_structural_pause(pace: str) -> bool:
        """Check if pace creates a structural pause (HOLD/LATER)"""
        return pace in [PaceState.HOLD.value, PaceState.LATER.value]
    
    @staticmethod
    def get_pace_options() -> List[str]:
        """Get all available pace options"""
        return [p.value for p in PaceState]
    
    @staticmethod
    def get_default_pace() -> str:
        """Get the default pace state"""
        return PaceState.NOW.value
