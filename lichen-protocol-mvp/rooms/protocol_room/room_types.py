"""
Protocol Room Types
Implements the Protocol Room Contract I/O specification using Python type hints
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Literal, Union


@dataclass
class ProtocolRoomInput:
    """Input contract for Protocol Room"""
    session_state_ref: str
    payload: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

    @classmethod
    def from_obj(cls, obj: Union["ProtocolRoomInput", Dict[str, Any]]) -> "ProtocolRoomInput":
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
class ProtocolRoomOutput:
    """Output contract for Protocol Room - must match exactly"""
    display_text: str
    next_action: Literal["continue"]


@dataclass
class ProtocolText:
    """Protocol text from canon"""
    protocol_id: str
    full_text: str
    theme_text: str
    scenario_text: str
    title: str
    description: str


@dataclass
class ScenarioMapping:
    """Scenario to protocol mapping"""
    scenario_label: str
    protocol_id: str
    relevance_score: int  # 1-10 scale


@dataclass
class IntegrityResult:
    """Result of integrity gate checks"""
    passed: bool
    stones_aligned: bool
    coherent: bool
    notes: List[str]


# Type aliases
ProtocolDepth = Literal["full", "theme", "scenario"]


# Protocol registry constants
class Protocols:
    """Static protocol registry for deterministic mapping"""
    RESOURCING_MINI_WALK = "resourcing_mini_walk"
    CLEARING_ENTRY = "clearing_entry"
    PACING_ADJUSTMENT = "pacing_adjustment"
    INTEGRATION_PAUSE = "integration_pause"
    DEEP_LISTENING = "deep_listening"
    BOUNDARY_SETTING = "boundary_setting"
    DEFAULT = "clearing_entry"


# Scenario registry constants
class Scenarios:
    """Static scenario registry for deterministic mapping"""
    OVERWHELM = "overwhelm"
    URGENCY = "urgency"
    BOUNDARY_VIOLATION = "boundary_violation"
    COMMUNICATION_BREAKDOWN = "communication_breakdown"
    DECISION_FATIGUE = "decision_fatigue"
    TEAM_CONFLICT = "team_conflict"
    PERSONAL_CRISIS = "personal_crisis"
    GROWTH_EDGE = "growth_edge"
