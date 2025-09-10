"""
Readiness Module
Implements Readiness Assessment theme from Diagnostic Room Protocol
"""

from rooms.diagnostic_room.room_types import ReadinessState


def assess_readiness(signals: 'DiagnosticSignals') -> ReadinessState:
    """
    Deterministic readiness assessment based on captured signals.
    No learning, no heuristics, no ML - only rule-based logic.
    """
    
    # If readiness_state is explicitly provided, use it
    if signals.readiness_state in ["NOW", "HOLD", "LATER", "SOFT_HOLD"]:
        return signals.readiness_state
    
    # Deterministic rules based on tone_label (explicit patterns only)
    if signals.tone_label == "overwhelm":
        return "HOLD"
    elif signals.tone_label == "urgency":
        return "NOW"
    elif signals.tone_label == "calm":
        return "NOW"
    elif signals.tone_label == "excitement":
        return "NOW"
    elif signals.tone_label == "worry":
        return "HOLD"
    
    # Deterministic rules based on residue_label
    if signals.residue_label == "unresolved_previous":
        return "HOLD"
    elif signals.residue_label == "previous_attempts":
        return "LATER"
    elif signals.residue_label == "deferring":
        return "LATER"
    
    # Default: safe assumption of readiness
    return "NOW"


def readiness_to_action(readiness: ReadinessState) -> str:
    """
    Maps readiness state to next_action.
    Deterministic mapping only.
    """
    if readiness == "NOW":
        return "continue"
    elif readiness == "HOLD":
        return "continue"  # Contract only allows "continue"
    elif readiness == "LATER":
        return "continue"  # Contract only allows "continue"
    elif readiness == "SOFT_HOLD":
        return "continue"  # Contract only allows "continue"
    else:
        return "continue"  # Default fallback
