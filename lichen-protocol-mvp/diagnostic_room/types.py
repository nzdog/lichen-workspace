"""
Diagnostic Room Types
Implements the Diagnostic Room Contract I/O specification using Python type hints
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Literal


@dataclass
class DiagnosticRoomInput:
    """Input contract for Diagnostic Room"""
    session_state_ref: str
    payload: Any


@dataclass
class DiagnosticRoomOutput:
    """Output contract for Diagnostic Room - must match exactly"""
    display_text: str
    next_action: Literal["continue"]


@dataclass
class DiagnosticSignals:
    """Diagnostic signals captured from input"""
    tone_label: str
    residue_label: str
    readiness_state: 'ReadinessState'


@dataclass
class ProtocolMapping:
    """Protocol mapping result with rationale"""
    suggested_protocol_id: str
    rationale: str


# Type aliases
ReadinessState = Literal["NOW", "HOLD", "LATER", "SOFT_HOLD"]


# Protocol registry constants
class Protocols:
    """Static protocol registry for deterministic mapping"""
    RESOURCING_MINI_WALK = "resourcing_mini_walk"
    CLEARING_ENTRY = "clearing_entry"
    PACING_ADJUSTMENT = "pacing_adjustment"
    INTEGRATION_PAUSE = "integration_pause"
    DEFAULT = "clearing_entry"
