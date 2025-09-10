"""
Mapping Module
Implements Protocol Mapping theme from Diagnostic Room Protocol
"""

from rooms.diagnostic_room.room_types import ProtocolMapping, DiagnosticSignals, Protocols


def map_to_protocol(signals: DiagnosticSignals) -> ProtocolMapping:
    """
    Deterministic protocol mapping based on captured signals.
    Rule-based selection only - no learning, no heuristics.
    """
    
    # Deterministic mapping rules based on tone_label
    if signals.tone_label == "overwhelm":
        protocol_id = Protocols.RESOURCING_MINI_WALK
        rationale = f"Tone: {signals.tone_label} → Resourcing needed"
    
    elif signals.tone_label == "urgency":
        protocol_id = Protocols.CLEARING_ENTRY
        rationale = f"Tone: {signals.tone_label} → Clearing for focus"
    
    elif signals.tone_label == "worry":
        protocol_id = Protocols.PACING_ADJUSTMENT
        rationale = f"Tone: {signals.tone_label} → Pacing adjustment needed"
    
    # Deterministic mapping rules based on residue_label
    elif signals.residue_label == "unresolved_previous":
        protocol_id = Protocols.INTEGRATION_PAUSE
        rationale = f"Residue: {signals.residue_label} → Integration pause"
    
    elif signals.residue_label == "previous_attempts":
        protocol_id = Protocols.CLEARING_ENTRY
        rationale = f"Residue: {signals.residue_label} → Clearing for fresh start"
    
    elif signals.residue_label == "deferring":
        protocol_id = Protocols.PACING_ADJUSTMENT
        rationale = f"Residue: {signals.residue_label} → Pacing adjustment"
    
    # Deterministic mapping rules based on readiness_state
    elif signals.readiness_state == "HOLD":
        protocol_id = Protocols.INTEGRATION_PAUSE
        rationale = f"Readiness: {signals.readiness_state} → Integration pause"
    
    elif signals.readiness_state == "LATER":
        protocol_id = Protocols.PACING_ADJUSTMENT
        rationale = f"Readiness: {signals.readiness_state} → Pacing adjustment"
    
    elif signals.readiness_state == "SOFT_HOLD":
        protocol_id = Protocols.CLEARING_ENTRY
        rationale = f"Readiness: {signals.readiness_state} → Gentle clearing"
    
    # Default mapping
    else:
        protocol_id = Protocols.DEFAULT
        rationale = f"Default: {Protocols.DEFAULT} for {signals.tone_label}/{signals.residue_label}"
    
    return ProtocolMapping(
        suggested_protocol_id=protocol_id,
        rationale=rationale
    )
