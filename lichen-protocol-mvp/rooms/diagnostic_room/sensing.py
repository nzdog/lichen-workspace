"""
Sensing Module
Implements Tone and Residue Sensing theme from Diagnostic Room Protocol
"""

from typing import Any
from rooms.diagnostic_room.room_types import DiagnosticSignals, ReadinessState


def capture_tone_and_residue(payload: Any) -> DiagnosticSignals:
    """
    Capture-only sensing: extracts tone_label and residue_label from input.
    No interpretation, no sentiment analysis, no heuristics.
    Returns "unspecified" if signals are not explicitly provided.
    """
    
    # Default values
    tone_label = "unspecified"
    residue_label = "unspecified"
    readiness_state: ReadinessState = "NOW"
    
    # If payload is a dict, look for explicit signals
    if isinstance(payload, dict):
        # Look for explicit tone_label
        if 'tone_label' in payload and isinstance(payload['tone_label'], str):
            tone_label = payload['tone_label']
        
        # Look for explicit residue_label
        if 'residue_label' in payload and isinstance(payload['residue_label'], str):
            residue_label = payload['residue_label']
        
        # Look for explicit readiness_state
        if 'readiness_state' in payload and payload['readiness_state'] in ["NOW", "HOLD", "LATER", "SOFT_HOLD"]:
            readiness_state = payload['readiness_state']
    
    # If payload is a string, check for simple flags (deterministic only)
    elif isinstance(payload, str):
        text = payload.lower()
        
        # Simple deterministic tone detection (explicit patterns only)
        if 'overwhelm' in text or 'overwhelmed' in text:
            tone_label = "overwhelm"
        elif 'urgency' in text or 'urgent' in text:
            tone_label = "urgency"
        elif 'calm' in text or 'peaceful' in text:
            tone_label = "calm"
        elif 'excitement' in text or 'excited' in text:
            tone_label = "excitement"
        elif 'worry' in text or 'worried' in text:
            tone_label = "worry"
        
        # Simple deterministic residue detection (explicit patterns only)
        if 'still' in text or 'again' in text:
            residue_label = "unresolved_previous"
        elif 'tried' in text or 'attempted' in text:
            residue_label = "previous_attempts"
        elif 'wait' in text or 'hold' in text:
            residue_label = "deferring"
    
    return DiagnosticSignals(
        tone_label=tone_label,
        residue_label=residue_label,
        readiness_state=readiness_state
    )
