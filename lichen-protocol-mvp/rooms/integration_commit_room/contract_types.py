from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Literal, Union
from enum import Enum
from datetime import datetime


class PaceState(Enum):
    """Pace states for commitments"""
    NOW = "NOW"
    HOLD = "HOLD"
    LATER = "LATER"
    SOFT_HOLD = "SOFT_HOLD"


class DeclineReason(Enum):
    """Reasons for declining operations"""
    MISSING_INTEGRATION = "missing_integration"
    INVALID_COMMITMENT_STRUCTURE = "invalid_commitment_structure"
    MISSING_PACE_STATE = "missing_pace_state"
    MEMORY_WRITE_FAILED = "memory_write_failed"
    INVALID_INPUT = "invalid_input"


@dataclass
class IntegrationData:
    """Integration data captured from the session"""
    integration_notes: str
    session_context: str
    key_insights: List[str] = field(default_factory=list)
    shifts_noted: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Commitment:
    """Individual commitment with required fields"""
    text: str
    context: str
    pace_state: PaceState
    session_ref: str
    timestamp: datetime = field(default_factory=datetime.now)
    commitment_id: Optional[str] = None


@dataclass
class MemoryWriteResult:
    """Result of memory write operation"""
    success: bool
    reason: str
    integration_written: bool = False
    commitments_written: int = 0
    error_details: Optional[str] = None


@dataclass
class IntegrationCommitRoomInput:
    """Input contract for Integration & Commit Room"""
    session_state_ref: str
    payload: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

    @classmethod
    def from_obj(cls, obj: Union["IntegrationCommitRoomInput", Dict[str, Any]]) -> "IntegrationCommitRoomInput":
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
class IntegrationCommitRoomOutput:
    """Output contract for Integration & Commit Room - must match exactly"""
    display_text: str
    next_action: Literal["continue"]


# Internal room state
@dataclass
class RoomState:
    """Internal room state for tracking progress"""
    integration_captured: bool = False
    commitments_recorded: bool = False
    pace_enforced: bool = False
    memory_written: bool = False
    integration_data: Optional[IntegrationData] = None
    commitments: List[Commitment] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# Decline response structure
@dataclass
class DeclineResponse:
    """Structured decline response"""
    reason: DeclineReason
    message: str
    details: Optional[str] = None
    required_fields: Optional[List[str]] = None
