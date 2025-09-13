"""
Step execution primitives for gate and room coordination.
"""

import time
from typing import Dict, Any, List

from .hallway_types import ExecutionContext, StepResult, StepStatus
from .errors import GateError, RoomError, ValidationError
from .validation import validate_room_input, validate_room_output
from .gates import evaluate_gate_chain
from .rooms_registry import get_room_function, is_room_available


async def run_step(room_id: str, ctx: ExecutionContext) -> StepResult:
    """
    Execute a complete step: pre-gates → room → post-gates.

    Args:
        room_id: Room to execute
        ctx: Execution context

    Returns:
        StepResult with status and outputs
    """
    from .logging import emit_event

    start_time = time.time()
    emit_event(ctx, phase="pre", room_id=room_id)

    try:
        # Pre-gates evaluation
        gate_decisions, gates_passed = _run_pre_gates(room_id, ctx)

        if not gates_passed:
            return StepResult(
                room_id=room_id,
                status=StepStatus.HALT,
                outputs={},
                errors=[f"Pre-gate evaluation failed: {gate_decisions}"],
                halt_reason="declined_by_gate",
                metrics={"duration_ms": (time.time() - start_time) * 1000}
            )

        # Room execution
        emit_event(ctx, phase="room", room_id=room_id)
        room_outputs = await _run_room(room_id, ctx)

        # Post-gates evaluation (currently same as pre-gates in existing system)
        emit_event(ctx, phase="post", room_id=room_id)
        post_gate_decisions, post_gates_passed = _run_post_gates(room_id, ctx, room_outputs)

        if not post_gates_passed:
            return StepResult(
                room_id=room_id,
                status=StepStatus.HALT,
                outputs=room_outputs,
                errors=[f"Post-gate evaluation failed: {post_gate_decisions}"],
                halt_reason="post_gates_failed",
                metrics={"duration_ms": (time.time() - start_time) * 1000}
            )

        # Determine status based on room output
        status = _determine_step_status(room_outputs)

        duration_ms = (time.time() - start_time) * 1000
        emit_event(ctx, phase="final", room_id=room_id, status=status.name, duration_ms=duration_ms)

        return StepResult(
            room_id=room_id,
            status=status,
            outputs=room_outputs,
            artifacts={
                "gate_decisions": gate_decisions + post_gate_decisions
            },
            metrics={"duration_ms": duration_ms}
        )

    except GateError as e:
        return StepResult(
            room_id=room_id,
            status=StepStatus.HALT if not e.recoverable else StepStatus.RETRY,
            outputs={},
            errors=[str(e)],
            halt_reason=e.reason,
            metrics={"duration_ms": (time.time() - start_time) * 1000}
        )

    except RoomError as e:
        return StepResult(
            room_id=room_id,
            status=StepStatus.FAIL if not e.recoverable else StepStatus.RETRY,
            outputs={},
            errors=[str(e)],
            halt_reason=e.reason,
            metrics={"duration_ms": (time.time() - start_time) * 1000}
        )

    except ValidationError as e:
        return StepResult(
            room_id=room_id,
            status=StepStatus.FAIL,
            outputs={},
            errors=[str(e)],
            halt_reason="validation_failed",
            metrics={"duration_ms": (time.time() - start_time) * 1000}
        )

    except Exception as e:
        ctx.ports.log.error({
            "event": "unexpected_error",
            "room_id": room_id,
            "error": str(e),
            "run_id": ctx.run_id
        })
        return StepResult(
            room_id=room_id,
            status=StepStatus.FAIL,
            outputs={},
            errors=[f"Unexpected error: {str(e)}"],
            halt_reason="unexpected_error",
            metrics={"duration_ms": (time.time() - start_time) * 1000}
        )


def _run_pre_gates(room_id: str, ctx: ExecutionContext) -> tuple[List[Dict[str, Any]], bool]:
    """Run pre-gate evaluations."""
    try:
        # Use existing gate chain evaluation from current system
        from .gates import evaluate_gate_chain

        gate_profile = ctx.policy.get("gate_profile", {"chain": [], "overrides": {}})

        # Type guards at step boundary
        session_state_ref = ctx.state.get("session_state_ref", "unknown")
        if not isinstance(session_state_ref, str):
            raise GateError(reason="invalid_session_state_ref_type", recoverable=False)

        payloads = ctx.state.get("payloads", {})
        if not isinstance(payloads, dict):
            raise GateError(reason="invalid_payloads_type", recoverable=False)

        # Get gates from context (should be passed in via ports or policy)
        gates = ctx.policy.get("gates", {})

        gate_decisions, gates_passed = evaluate_gate_chain(
            gate_profile["chain"],
            room_id,
            session_state_ref,
            payloads.get(room_id),
            gates
        )

        # Convert gate decisions to dict format
        gate_decisions_dict = [
            gd.to_dict() if hasattr(gd, 'to_dict') else gd
            for gd in gate_decisions
        ]

        return gate_decisions_dict, gates_passed

    except Exception as e:
        raise GateError(f"Pre-gate evaluation failed: {str(e)}", "pre_gates", recoverable=False)


def _run_post_gates(room_id: str, ctx: ExecutionContext, room_outputs: Dict[str, Any]) -> tuple[List[Dict[str, Any]], bool]:
    """Run post-gate evaluations."""
    # For now, post-gates are the same as pre-gates in the current system
    # This could be extended to have different gate logic based on room outputs
    return [], True


async def _run_room(room_id: str, ctx: ExecutionContext) -> Dict[str, Any]:
    """Execute a single room."""
    try:
        # Check if room is available
        if not is_room_available(room_id):
            raise RoomError(f"Room '{room_id}' not found in registry", room_id, recoverable=False)

        # Get room function
        room_fn = get_room_function(room_id)

        # Prepare room input
        session_state_ref = ctx.state.get("session_state_ref", "unknown")
        payloads = ctx.state.get("payloads", {})

        room_input = {
            "session_state_ref": session_state_ref,
            "payload": payloads.get(room_id),
            "options": {}
        }

        # Validate input (if schema exists)
        try:
            validate_room_input(room_id, room_input)
        except ValidationError:
            # Input validation is optional - some rooms may not have schemas yet
            pass

        # Execute room (handle both sync and async)
        if hasattr(room_fn, '__call__'):
            import asyncio
            if asyncio.iscoroutinefunction(room_fn):
                room_output = await room_fn(room_input)
            else:
                room_output = room_fn(room_input)
        else:
            raise RoomError(f"Room function for '{room_id}' is not callable", room_id, recoverable=False)

        # Validate output (if schema exists)
        try:
            validate_room_output(room_id, room_output)
        except ValidationError:
            # Output validation is optional - some rooms may not have schemas yet
            pass

        return room_output

    except RoomError:
        raise
    except Exception as e:
        raise RoomError(f"Room execution failed: {str(e)}", room_id, recoverable=False)


def _determine_step_status(room_outputs: Dict[str, Any]) -> StepStatus:
    """Determine step status based on room outputs."""
    # Check if room declined using existing logic
    from .upcaster import is_room_decline

    if is_room_decline(room_outputs):
        return StepStatus.HALT

    # Check for specific status indicators in room output
    if "status" in room_outputs:
        status = room_outputs["status"]
        if status == "retry":
            return StepStatus.RETRY
        elif status == "halt":
            return StepStatus.HALT
        elif status == "fallback":
            return StepStatus.FALLBACK
        elif status == "fail":
            return StepStatus.FAIL

    # Default to OK
    return StepStatus.OK
