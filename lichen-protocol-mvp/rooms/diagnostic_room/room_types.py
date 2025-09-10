"""
Diagnostic Room Types
Canonical type definitions for Diagnostic Room Protocol and Contract
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Literal, Union


@dataclass
class DiagnosticRoomInput:
    """Input structure for Diagnostic Room"""
    session_state_ref: str
    payload: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

    @classmethod
    def from_obj(cls, obj: Union["DiagnosticRoomInput", Dict[str, Any]]) -> "DiagnosticRoomInput":
        if isinstance(obj, cls):
            return obj
        if not isinstance(obj, dict):
            raise TypeError(f"{cls.__name__}.from_obj expected dict or {cls.__name__}, got {type(obj)}")
        return cls(
            session_state_ref=obj.get("session_state_ref", ""),
            payload=obj.get("payload"),
            options=obj.get("options"),
        )


@dataclass
class DiagnosticRoomOutput:
    """Output structure for Diagnostic Room"""
    display_text: str
    next_action: Literal["continue"]


@dataclass
class DiagnosticSignals:
    """Captured diagnostic signals"""
    tone_label: str
    residue_label: str
    readiness_state: 'ReadinessState'


@dataclass
class ProtocolMapping:
    """Protocol mapping result"""
    suggested_protocol_id: str
    rationale: str


# Readiness states
ReadinessState = Literal["NOW", "HOLD", "LATER", "SOFT_HOLD"]


class Protocols:
    """Protocol constants"""
    RESOURCING_MINI_WALK = "resourcing_mini_walk"
    CLEARING_ENTRY = "clearing_entry"
    PACING_ADJUSTMENT = "pacing_adjustment"
    INTEGRATION_PAUSE = "integration_pause"
    DEFAULT = "clearing_entry"