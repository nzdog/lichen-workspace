from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Literal, Union
from enum import Enum
from datetime import datetime


class MemoryScope(Enum):
    """Memory scope for retrieval operations"""
    SESSION = "session"
    PROTOCOL = "protocol"
    GLOBAL = "global"


class UserAction(Enum):
    """User actions for memory control"""
    PIN = "pin"
    EDIT = "edit"
    DELETE = "delete"
    VIEW = "view"


@dataclass
class CaptureData:
    """Minimal structured data for memory capture"""
    tone_label: str = "unspecified"
    residue_label: str = "unspecified"
    readiness_state: str = "unspecified"
    integration_notes: str = "unspecified"
    commitments: str = "unspecified"
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str = "unspecified"
    protocol_id: Optional[str] = None


@dataclass
class MemoryItem:
    """Individual memory item with metadata"""
    item_id: str
    capture_data: CaptureData
    is_pinned: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    deleted_at: Optional[datetime] = None


@dataclass
class GovernanceResult:
    """Result of governance rule application"""
    is_allowed: bool
    reason: str
    filtered_data: Optional[CaptureData] = None


@dataclass
class MemoryRoomInput:
    """Input contract for Memory Room"""
    session_state_ref: str
    payload: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

    @classmethod
    def from_obj(cls, obj: Union["MemoryRoomInput", Dict[str, Any]]) -> "MemoryRoomInput":
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
class MemoryRoomOutput:
    """Output contract for Memory Room - must match exactly"""
    display_text: str
    next_action: Literal["continue"]


# Internal memory session state
@dataclass
class MemorySession:
    """Internal memory session state"""
    session_id: str
    items: List[MemoryItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)


# Memory query result
@dataclass
class MemoryQuery:
    """Query parameters for memory retrieval"""
    scope: MemoryScope
    session_id: Optional[str] = None
    protocol_id: Optional[str] = None
    include_deleted: bool = False
    limit: Optional[int] = None


# Memory operation result
@dataclass
class MemoryOperationResult:
    """Result of memory operations"""
    success: bool
    message: str
    affected_items: List[MemoryItem] = field(default_factory=list)
    error_details: Optional[str] = None
