"""
Entry Room Types
Implements the Entry Room Contract I/O specification using Python type hints
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union, Literal
from abc import ABC, abstractmethod


@dataclass
class EntryRoomInput:
    """Input contract for Entry Room"""
    session_state_ref: str
    payload: Any


@dataclass
class EntryRoomOutput:
    """Output contract for Entry Room - must match exactly"""
    display_text: str
    next_action: Literal["continue", "hold", "later"]


@dataclass
class GateResult:
    """Result from a gate execution"""
    ok: bool
    text: str
    notes: Optional[List[str]] = None


@dataclass
class DiagnosticRecord:
    """Diagnostic information captured during processing"""
    timestamp: str
    session_id: str
    room_id: str
    tone: Optional[str] = None
    residue: Optional[str] = None
    readiness: Optional[str] = None


@dataclass
class EntryRoomContext:
    """Internal context for Entry Room processing"""
    session_id: str
    pace_state: 'PaceState'
    consent_granted: bool
    diagnostics_enabled: bool


# Type aliases
PaceState = Literal["NOW", "HOLD", "LATER", "SOFT_HOLD"]


# Abstract base classes for policies
class GateAdapter(ABC):
    """Abstract base class for gate implementations"""
    
    @abstractmethod
    async def run(self, text: str, ctx: Dict[str, Any]) -> GateResult:
        """Run the gate on the given text"""
        pass


class PacePolicy(ABC):
    """Abstract base class for pace policies"""
    
    @abstractmethod
    async def apply_pace_gate(self, ctx: EntryRoomContext) -> PaceState:
        """Apply pace gate to determine session pacing"""
        pass


class ConsentPolicy(ABC):
    """Abstract base class for consent policies"""
    
    @abstractmethod
    async def enforce_consent(self, ctx: EntryRoomContext) -> Literal["YES", "HOLD", "LATER"]:
        """Enforce explicit consent before proceeding"""
        pass


class DiagnosticsPolicy(ABC):
    """Abstract base class for diagnostics policies"""
    
    @abstractmethod
    async def capture_diagnostics(
        self,
        input_data: EntryRoomInput,
        interim: EntryRoomContext,
        output: EntryRoomOutput
    ) -> Optional[DiagnosticRecord]:
        """Capture diagnostic information when enabled"""
        pass


class CompletionPolicy(ABC):
    """Abstract base class for completion policies"""
    
    @abstractmethod
    def append_completion_marker(self, text: str) -> str:
        """Append completion marker to display text"""
        pass


class ReflectionPolicy(ABC):
    """Abstract base class for reflection policies"""
    
    @abstractmethod
    def reflect_verbatim(self, payload: Any) -> List[str]:
        """Reflect input exactly without interpretation"""
        pass
