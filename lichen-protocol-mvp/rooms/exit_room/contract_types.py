from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Literal, Union
from enum import Enum
from datetime import datetime


class ExitReason(Enum):
    """Reasons for session exit"""
    NORMAL_COMPLETION = "normal_completion"
    ABORTED = "aborted"
    FORCE_CLOSED = "force_closed"
    ERROR_CONDITION = "error_condition"


class DeclineReason(Enum):
    """Reasons for declining operations"""
    COMPLETION_NOT_SATISFIED = "completion_not_satisfied"
    DIAGNOSTICS_FAILED = "diagnostics_failed"
    MEMORY_COMMIT_FAILED = "memory_commit_failed"
    STATE_RESET_FAILED = "state_reset_failed"
    INVALID_INPUT = "invalid_input"


@dataclass
class ExitDiagnostics:
    """Final session diagnostics captured at exit"""
    session_id: str
    exit_reason: ExitReason
    completion_satisfied: bool
    diagnostics_captured: bool
    memory_committed: bool
    state_reset: bool
    final_timestamp: datetime = field(default_factory=datetime.now)
    session_duration: Optional[float] = None
    error_summary: Optional[str] = None


@dataclass
class MemoryCommitData:
    """Data to be committed to memory at exit"""
    session_id: str
    exit_reason: ExitReason
    diagnostics: ExitDiagnostics
    closure_flag: bool = True
    final_state_snapshot: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExitRoomInput:
    """Input contract for Exit Room"""
    session_state_ref: str
    payload: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

    @classmethod
    def from_obj(cls, obj: Union["ExitRoomInput", Dict[str, Any]]) -> "ExitRoomInput":
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
class ExitRoomOutput:
    """Output contract for Exit Room - must match exactly"""
    display_text: str
    next_action: Literal["continue"]


# Internal room state
@dataclass
class ExitRoomState:
    """Internal room state for tracking exit progress"""
    completion_enforced: bool = False
    diagnostics_captured: bool = False
    memory_committed: bool = False
    state_reset: bool = False
    exit_diagnostics: Optional[ExitDiagnostics] = None
    errors: List[str] = field(default_factory=list)


# Decline response structure
@dataclass
class DeclineResponse:
    """Structured decline response"""
    reason: DeclineReason
    message: str
    details: Optional[str] = None
    required_fields: Optional[List[str]] = None


# Session state for exit processing
@dataclass
class SessionState:
    """Session state for exit processing"""
    session_id: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    completion_required: bool = True
    diagnostics_enabled: bool = True
    temporary_buffers: Dict[str, Any] = field(default_factory=dict)
    session_data: Dict[str, Any] = field(default_factory=dict)


# Exit operation result
@dataclass
class ExitOperationResult:
    """Result of exit operations"""
    success: bool
    message: str
    diagnostics: Optional[ExitDiagnostics] = None
    memory_commit_result: Optional[bool] = None
    state_reset_result: Optional[bool] = None
    error_details: Optional[str] = None
