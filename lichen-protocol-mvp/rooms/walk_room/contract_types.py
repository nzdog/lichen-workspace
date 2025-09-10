"""
Contract Types Module
Defines all data structures for Walk Room contracts and internal state
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Literal, Union
from enum import Enum


class WalkState(Enum):
    """Walk execution state machine"""
    PENDING = "pending"
    IN_STEP = "in_step"
    COMPLETED = "completed"


class PaceState(Enum):
    """Pace states for walk steps"""
    NOW = "NOW"
    HOLD = "HOLD"
    LATER = "LATER"
    SOFT_HOLD = "SOFT_HOLD"


@dataclass
class WalkStep:
    """Individual step in a protocol walk"""
    step_index: int
    title: str
    content: str
    description: str
    estimated_time: Optional[int] = None  # minutes


@dataclass
class StepDiagnostics:
    """Diagnostics captured at each step"""
    step_index: int
    tone_label: str
    residue_label: str
    readiness_state: str


@dataclass
class CompletionPrompt:
    """Completion prompt for walk closure"""
    prompt_text: str
    response_required: bool = True


@dataclass
class WalkRoomInput:
    """Input contract for Walk Room"""
    session_state_ref: str
    payload: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

    @classmethod
    def from_obj(cls, obj: Union["WalkRoomInput", Dict[str, Any]]) -> "WalkRoomInput":
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
class WalkRoomOutput:
    """Output contract for Walk Room - must match exactly"""
    display_text: str
    next_action: Literal["continue"]


# Protocol structure for testing and development
@dataclass
class ProtocolStructure:
    """Protocol structure with ordered steps"""
    protocol_id: str
    title: str
    description: str
    steps: List[WalkStep]
    completion_prompt: CompletionPrompt


# Internal walk session state
@dataclass
class WalkSession:
    """Internal walk session state"""
    current_step_index: int
    walk_state: WalkState
    steps: List[WalkStep]
    diagnostics: List[StepDiagnostics]
    completion_confirmed: bool
    protocol_id: str
