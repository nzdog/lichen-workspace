"""
Core types and data structures for the Hallway Protocol.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Protocol


class StepStatus(Enum):
    """Status of a step execution."""
    OK = auto()
    RETRY = auto()
    HALT = auto()
    FALLBACK = auto()
    FAIL = auto()


@dataclass
class StepResult:
    """Result of executing a single room step."""
    room_id: str
    status: StepStatus
    outputs: Dict[str, Any]
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    halt_reason: Optional[str] = None


@dataclass
class ExecutionContext:
    """Context maintained throughout a hallway execution."""
    run_id: str
    correlation_id: str
    rooms_to_run: List[str]
    state: Dict[str, Any]
    budgets: Dict[str, float]
    ports: "Ports"
    policy: Dict[str, Any]
    events: List[Dict[str, Any]] = field(default_factory=list)
    usage: Dict[str, float] = field(default_factory=lambda: {"tokens": 0.0, "time_ms": 0.0, "retries": 0.0})

    def add_step(self, step_result: StepResult) -> None:
        """Add a step result to the execution context."""
        # Update state with step outputs if successful
        if step_result.status == StepStatus.OK and step_result.outputs:
            self.state.update(step_result.outputs)

        # Update usage counters based on step metrics
        if step_result.metrics:
            for metric, value in step_result.metrics.items():
                if metric in self.usage:
                    self.usage[metric] += value


@dataclass
class FinalOutput:
    """Final output of a hallway execution."""
    run_id: str
    outputs: Dict[str, Any]
    events: List[Dict[str, Any]]


# Forward reference for Ports protocol
class Ports(Protocol):
    """Bundle of all IO interfaces needed by the hallway."""
    pass
