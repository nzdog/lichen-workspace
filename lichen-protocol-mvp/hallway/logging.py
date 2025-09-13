"""
Structured event logging helpers for the Hallway Protocol.
"""

from typing import Dict, Any
from .hallway_types import ExecutionContext


def emit_event(ctx: ExecutionContext, **fields) -> None:
    """
    Emit a structured event to both context and logger.

    Args:
        ctx: Execution context
        **fields: Event fields to log
    """
    # Add standard fields with budget information
    event = {
        "run_id": ctx.run_id,
        "correlation_id": ctx.correlation_id,
        "timestamp": ctx.ports.clock.now_iso(),
        "budgets_remaining": {k: v - ctx.usage.get(k, 0.0) for k, v in ctx.budgets.items()},
        **fields
    }

    # Add to context events for audit trail
    ctx.events.append(event)

    # Log to external system
    if event.get("phase") in ["error", "halt"] or "error" in event:
        ctx.ports.log.error(event)
    else:
        ctx.ports.log.info(event)

    # Update metrics if applicable
    if "duration_ms" in event:
        ctx.ports.metrics.timing(
            "hallway.step.duration",
            event["duration_ms"],
            room_id=event.get("room_id", "unknown"),
            status=event.get("status", "unknown")
        )

    if event.get("phase") == "step_done":
        ctx.ports.metrics.incr(
            "hallway.step.completed",
            room_id=event.get("room_id", "unknown"),
            status=event.get("status", "unknown")
        )

    if event.get("phase") == "halt":
        ctx.ports.metrics.incr(
            "hallway.execution.halted",
            reason=event.get("reason", "unknown")
        )


def emit_budget_update(ctx: ExecutionContext, budget_type: str, used: float, remaining: float) -> None:
    """Emit a budget update event."""
    emit_event(
        ctx,
        phase="budget_update",
        budget_type=budget_type,
        used=used,
        remaining=remaining
    )

    ctx.ports.metrics.gauge(
        f"hallway.budget.{budget_type}.remaining",
        remaining,
        run_id=ctx.run_id
    )


def emit_room_metrics(ctx: ExecutionContext, room_id: str, metrics: Dict[str, Any]) -> None:
    """Emit room-specific metrics."""
    for metric_name, value in metrics.items():
        if isinstance(value, (int, float)):
            if "time" in metric_name or "duration" in metric_name:
                ctx.ports.metrics.timing(
                    f"hallway.room.{metric_name}",
                    value,
                    room_id=room_id
                )
            else:
                ctx.ports.metrics.gauge(
                    f"hallway.room.{metric_name}",
                    value,
                    room_id=room_id
                )


def emit_gate_decision(ctx: ExecutionContext, room_id: str, gate_name: str, allowed: bool, reason: str) -> None:
    """Emit a gate decision event."""
    emit_event(
        ctx,
        phase="gate_decision",
        room_id=room_id,
        gate_name=gate_name,
        allowed=allowed,
        reason=reason
    )

    ctx.ports.metrics.incr(
        "hallway.gate.decision",
        gate=gate_name,
        allowed=str(allowed).lower(),
        room_id=room_id
    )
