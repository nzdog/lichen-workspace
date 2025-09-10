"""
Pure control flow orchestrator for the Hallway Protocol.
"""

from typing import Dict, Any, List, Optional

from .types import ExecutionContext, FinalOutput, StepStatus, StepResult
from .steps import run_step
from .logging import emit_event
from .errors import BudgetExceededError


async def run_hallway(ctx: ExecutionContext) -> FinalOutput:
    """
    Execute the hallway protocol with pure control flow.

    Args:
        ctx: Execution context with all necessary state and dependencies

    Returns:
        Final output with results and audit trail
    """
    emit_event(ctx, phase="start", rooms_planned=len(ctx.rooms_to_run))

    try:
        for room_id in ctx.rooms_to_run:
            # Check budgets before each step
            if _exceeded_budgets(ctx):
                emit_event(ctx, phase="halt", reason="budget_exceeded", room_id=room_id)
                break

            emit_event(ctx, phase="step_start", room_id=room_id)

            # Execute the step
            step_result = await run_step(room_id, ctx)
            ctx.add_step(step_result)

            emit_event(
                ctx,
                phase="step_done",
                room_id=room_id,
                status=step_result.status.name,
                duration_ms=step_result.metrics.get("duration_ms", 0)
            )

            # Handle step result based on status
            if step_result.status == StepStatus.FAIL:
                emit_event(ctx, phase="halt", reason="step_failed", room_id=room_id)
                break

            elif step_result.status == StepStatus.HALT:
                # Honor stop_on_decline policy
                stop_on_decline = ctx.policy.get("stop_on_decline", True)
                if stop_on_decline:
                    emit_event(ctx, phase="halt", reason="step_halted", room_id=room_id, halt_reason=step_result.halt_reason)
                    break
                else:
                    # Continue to next room if policy allows
                    emit_event(ctx, phase="decline_continue", reason="step_halted", room_id=room_id, halt_reason=step_result.halt_reason)

            elif step_result.status == StepStatus.RETRY:
                # Implement retry logic if needed
                retry_count = step_result.metrics.get("retry_count", 0)
                max_retries = ctx.policy.get("max_retries", 3)

                if retry_count < max_retries:
                    emit_event(ctx, phase="retry", room_id=room_id, attempt=retry_count + 1)
                    # Could implement retry here, for now just continue
                else:
                    emit_event(ctx, phase="halt", reason="max_retries_exceeded", room_id=room_id)
                    break

            elif step_result.status == StepStatus.FALLBACK:
                # Implement fallback logic
                emit_event(ctx, phase="fallback", room_id=room_id)
                _handle_fallback(ctx, step_result)

            # For OK status, just continue to next room

            # Update state if room provided new session state
            if "session_state_ref" in step_result.outputs:
                ctx.state["session_state_ref"] = step_result.outputs["session_state_ref"]

        # Build final output
        final_output = _build_final_output(ctx)
        emit_event(ctx, phase="end", success=True, total_steps=len(ctx.events))

        return final_output

    except Exception as e:
        emit_event(ctx, phase="error", error=str(e))
        ctx.ports.log.error({
            "event": "orchestrator_error",
            "run_id": ctx.run_id,
            "error": str(e)
        })
        raise


def _exceeded_budgets(ctx: ExecutionContext) -> bool:
    """Check if any budget limits have been exceeded."""
    for k, limit in ctx.budgets.items():
        if ctx.usage.get(k, 0.0) > float(limit):
            return True
    return False


def _handle_fallback(ctx: ExecutionContext, step_result: StepResult) -> None:
    """Handle fallback logic for a step."""
    # For now, just log the fallback
    # This could be extended to modify the execution plan
    ctx.ports.log.info({
        "event": "fallback_handled",
        "run_id": ctx.run_id,
        "room_id": step_result.room_id,
        "reason": step_result.halt_reason
    })


def _build_final_output(ctx: ExecutionContext) -> FinalOutput:
    """Build the final output from execution context."""
    # Collect all step outputs that are marked as successful
    final_outputs = {}

    # Include final session state
    if "session_state_ref" in ctx.state:
        final_outputs["final_state_ref"] = ctx.state["session_state_ref"]

    # Include any other accumulated outputs
    for key, value in ctx.state.items():
        if not key.startswith("_") and key not in ["payloads", "session_state_ref"]:
            final_outputs[key] = value

    # Build audit trail
    steps = []
    step_count = 0
    for event in ctx.events:
        if event.get("phase") == "step_done":
            step_count += 1
            steps.append({
                "step": step_count,
                "room_id": event.get("room_id"),
                "status": event.get("status"),
                "duration_ms": event.get("duration_ms", 0),
                "timestamp": event.get("timestamp")
            })

    # Determine completion status
    completed = not any(
        event.get("phase") == "halt" or event.get("phase") == "error"
        for event in ctx.events
    )

    final_outputs["contract_version"] = "0.2.0"
    final_outputs["steps"] = steps
    final_outputs["completed"] = completed
    final_outputs["exit_summary"] = {
        "completed": completed,
        "decline": None if completed else _extract_decline_reason(ctx),
        "auditable_hash_chain": _build_audit_chain(steps)
    }

    return FinalOutput(
        run_id=ctx.run_id,
        outputs=final_outputs,
        events=ctx.events
    )


def _extract_decline_reason(ctx: ExecutionContext) -> Optional[Dict[str, Any]]:
    """Extract decline reason from context events."""
    for event in ctx.events:
        if event.get("phase") == "halt":
            return {
                "reason": event.get("reason", "unknown"),
                "message": f"Execution halted: {event.get('reason', 'unknown')}",
                "details": {
                    "room_id": event.get("room_id"),
                    "event": event
                }
            }
    return None


def _build_audit_chain(steps: List[Dict[str, Any]]) -> List[str]:
    """Build audit hash chain from steps."""
    # Simple implementation - in production would use proper cryptographic hashes
    import hashlib

    chain = []
    prev_hash = "genesis"

    for step in steps:
        # Create deterministic hash from step data
        step_data = f"{prev_hash}:{step.get('room_id')}:{step.get('status')}:{step.get('timestamp')}"
        step_hash = hashlib.sha256(step_data.encode()).hexdigest()[:16]
        chain.append(step_hash)
        prev_hash = step_hash

    return chain
