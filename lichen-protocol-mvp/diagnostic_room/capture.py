"""
Capture Module
Implements Silent Capture theme from Diagnostic Room Protocol
"""

from typing import Dict, Any, Optional
from .types import DiagnosticSignals, ProtocolMapping


def capture_diagnostics(
    signals: DiagnosticSignals,
    mapping: ProtocolMapping,
    diagnostics_enabled: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Minimal diagnostic capture and memory write.
    If diagnostics_enabled, writes structured data; if disabled, skips cleanly.
    Never blocks flow.
    """
    
    if not diagnostics_enabled:
        return None
    
    # Minimal structured data as specified
    diagnostic_data = {
        "tone_label": signals.tone_label,
        "residue_label": signals.residue_label,
        "readiness_state": signals.readiness_state,
        "suggested_protocol_id": mapping.suggested_protocol_id
    }
    
    # In a real implementation, this would write to memory/storage
    # For now, we just return the data structure
    return diagnostic_data


def format_display_text(signals: DiagnosticSignals, mapping: ProtocolMapping) -> str:
    """
    Formats the display text based on captured signals and mapping.
    Simple, deterministic formatting.
    """
    
    lines = [
        f"Tone: {signals.tone_label}",
        f"Residue: {signals.residue_label}",
        f"Readiness: {signals.readiness_state}",
        "",
        f"Suggested Protocol: {mapping.suggested_protocol_id}",
        f"Rationale: {mapping.rationale}"
    ]
    
    return "\n".join(lines)
