"""
Hallway Protocol Implementation
Deterministic multi-room session orchestrator with gate enforcement and audit trails
"""

import asyncio
import importlib
import time
from typing import Dict, Any, List, Optional
from .gates import evaluate_gate_chain, CoherenceGate
from .upcaster import upcast_v01_to_v02, is_room_decline
from .audit import build_audit_chain
from .rooms_registry import get_room_function, is_room_available
from .schema_utils import validate_room_output, create_schema_decline

# New orchestrator imports
from .orchestrator import run_hallway
from .hallway_types import ExecutionContext
from .adapters import build_ports


class HallwayOrchestrator:
    """
    Main orchestrator for the Hallway Protocol.
    Runs the canonical sequence of rooms, enforces gate chains, and returns v0.2 envelopes.
    """

    def __init__(self, contract: Dict[str, Any], gates: Optional[Dict[str, Any]] = None):
        """
        Initialize the HallwayOrchestrator.

        Args:
            contract: Hallway contract configuration
            gates: Dictionary mapping gate names to gate implementations
        """
        self.contract = contract
        self.gates = gates or {"coherence_gate": CoherenceGate()}
        self.sequence = contract.get("sequence", [])
        self.gate_profile = contract.get("gate_profile", {"chain": [], "overrides": {}})

    async def run(
        self,
        session_state_ref: str,
        payloads: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run the hallway protocol with the given session state and options.

        Args:
            session_state_ref: Reference to the session state
            payloads: Optional per-room payload map keyed by room_id
            options: Optional configuration options

        Returns:
            Dict that validates against the Hallway v0.2 contract
        """
        # NEW: Use refactored orchestrator if enabled
        use_new_orchestrator = options.get("use_new_orchestrator", False) if options else False

        if use_new_orchestrator:
            return await self._run_new_orchestrator(session_state_ref, payloads, options)

        # LEGACY: Keep existing implementation for backward compatibility
        # Prepare options with defaults
        options = options or {}
        stop_on_decline = options.get("stop_on_decline", True)
        dry_run = options.get("dry_run", False)
        mini_walk = options.get("mini_walk", False)
        rooms_subset = options.get("rooms_subset", [])

        # Determine which rooms to run
        rooms_to_run = self._determine_rooms_to_run(rooms_subset, mini_walk)

        # Initialize results
        steps = []
        last_hash = None
        final_state_ref = session_state_ref

        # Run each room in sequence
        for room_id in rooms_to_run:
            # Evaluate gate chain
            gate_decisions, gates_passed = evaluate_gate_chain(
                self.gate_profile["chain"],
                room_id,
                session_state_ref,
                payloads.get(room_id) if payloads else None,
                self.gates
            )

            # Convert gate decisions to dict format
            gate_decisions_dict = [gd.to_dict() if hasattr(gd, 'to_dict') else gd for gd in gate_decisions]

            # If gates failed and we should stop on decline
            if not gates_passed:
                # Create decline step result
                decline_step = upcast_v01_to_v02(
                    room_id=room_id,
                    room_output_v01={
                        "error": "Gate chain evaluation failed",
                        "gate_decisions": gate_decisions_dict
                    },
                    status="decline",
                    gate_decisions=gate_decisions_dict,
                    prev_hash=last_hash
                )
                steps.append(decline_step)
                last_hash = decline_step["audit"]["step_hash"]

                # If we should stop on decline, exit now
                if stop_on_decline:
                    exit_summary = self._build_exit_summary(
                        completed=False,
                        decline={
                            "reason": "gate_chain_failed",
                            "message": f"Gate chain evaluation failed for room {room_id}",
                            "details": {"room_id": room_id, "gate_decisions": gate_decisions_dict}
                        },
                        steps=steps
                    )

                    return self._build_hallway_output(steps, final_state_ref, exit_summary)

                # If not stopping on decline, continue to next room
                continue

            # If dry run, skip actual room execution
            if dry_run:
                mock_output = {"dry_run": True, "room_id": room_id}
                step_result = upcast_v01_to_v02(
                    room_id=room_id,
                    room_output_v01=mock_output,
                    status="ok",
                    gate_decisions=gate_decisions_dict,
                    prev_hash=last_hash
                )
                steps.append(step_result)
                last_hash = step_result["audit"]["step_hash"]
                continue

            # Check if room is available in registry
            if not is_room_available(room_id):
                # Room not found in registry - create decline step
                decline_output = create_schema_decline(
                    room_id,
                    f"Room '{room_id}' not found in registry"
                )
                step_result = upcast_v01_to_v02(
                    room_id=room_id,
                    room_output_v01=decline_output,
                    status="decline",
                    gate_decisions=gate_decisions_dict,
                    prev_hash=last_hash
                )
                steps.append(step_result)
                last_hash = step_result["audit"]["step_hash"]

                if stop_on_decline:
                    exit_summary = self._build_exit_summary(
                        completed=False,
                        decline={
                            "reason": "room_not_found",
                            "message": f"Room '{room_id}' not found in registry",
                            "details": {"room_id": room_id}
                        },
                        steps=steps
                    )
                    return self._build_hallway_output(steps, final_state_ref, exit_summary)
                continue

            # Run the real room
            try:
                room_output = await self._run_room(room_id, session_state_ref, payloads)
            except Exception as e:
                # Room execution failed - create decline step
                decline_output = create_schema_decline(
                    room_id,
                    f"Room execution failed: {str(e)}"
                )
                step_result = upcast_v01_to_v02(
                    room_id=room_id,
                    room_output_v01=decline_output,
                    status="decline",
                    gate_decisions=gate_decisions_dict,
                    prev_hash=last_hash
                )
                steps.append(step_result)
                last_hash = step_result["audit"]["step_hash"]

                if stop_on_decline:
                    exit_summary = self._build_exit_summary(
                        completed=False,
                        decline={
                            "reason": "room_execution_failed",
                            "message": f"Room '{room_id}' execution failed",
                            "details": {"room_id": room_id, "error": str(e)}
                        },
                        steps=steps
                    )
                    return self._build_hallway_output(steps, final_state_ref, exit_summary)
                continue

            # Validate room output against its schema
            is_valid, validation_error = validate_room_output(room_id, room_output)
            if not is_valid:
                # Schema validation failed - create decline step
                decline_output = create_schema_decline(room_id, validation_error)
                step_result = upcast_v01_to_v02(
                    room_id=room_id,
                    room_output_v01=decline_output,
                    status="decline",
                    gate_decisions=gate_decisions_dict,
                    prev_hash=last_hash
                )
                steps.append(step_result)
                last_hash = step_result["audit"]["step_hash"]

                if stop_on_decline:
                    exit_summary = self._build_exit_summary(
                        completed=False,
                        decline={
                            "reason": "schema_validation_failed",
                            "message": f"Room '{room_id}' output failed schema validation",
                            "details": {"room_id": room_id, "error": validation_error}
                        },
                        steps=steps
                    )
                    return self._build_hallway_output(steps, final_state_ref, exit_summary)
                continue

            # Determine status based on room output
            status = "ok"
            if is_room_decline(room_output):
                status = "decline"

            # Create step result
            step_result = upcast_v01_to_v02(
                room_id=room_id,
                room_output_v01=room_output,
                status=status,
                gate_decisions=gate_decisions_dict,
                prev_hash=last_hash
            )

            steps.append(step_result)
            last_hash = step_result["audit"]["step_hash"]

            # Update final state ref if room provides one
            if "session_state_ref" in room_output:
                final_state_ref = room_output["session_state_ref"]

            # If room declined and we should stop on decline
            if status == "decline" and stop_on_decline:
                exit_summary = self._build_exit_summary(
                    completed=False,
                    decline={
                        "reason": "room_declined",
                        "message": f"Room {room_id} declined to proceed",
                        "details": {"room_id": room_id, "room_output": room_output}
                    },
                    steps=steps
                )

                return self._build_hallway_output(steps, final_state_ref, exit_summary)

            # Note: Exception handling is commented out since we're using mock output
            # The mock output approach avoids room execution errors

        # All rooms completed successfully
        exit_summary = self._build_exit_summary(
            completed=True,
            decline=None,
            steps=steps
        )

        return self._build_hallway_output(steps, final_state_ref, exit_summary)

    async def _run_new_orchestrator(
        self,
        session_state_ref: str,
        payloads: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run using the new refactored orchestrator."""

        # Prepare options with defaults
        options = options or {}
        mini_walk = options.get("mini_walk", False)
        rooms_subset = options.get("rooms_subset", [])

        # Determine which rooms to run
        rooms_to_run = self._determine_rooms_to_run(rooms_subset, mini_walk)

        # Build ports (using mocks for now)
        ports = build_ports()

        # Create execution context
        ctx = ExecutionContext(
            run_id=ports.ids.new_id("hallway"),
            correlation_id=ports.ids.new_id("corr"),
            rooms_to_run=rooms_to_run,
            state={
                "session_state_ref": session_state_ref,
                "payloads": payloads or {}
            },
            budgets={
                "tokens": 10000.0,
                "time_ms": 30000.0,
                "retries": 3.0
            },
            ports=ports,
            policy={
                "gate_profile": self.gate_profile,
                "gates": self.gates,
                "max_retries": 3,
                "stop_on_decline": options.get("stop_on_decline", True)
            }
        )

        # Run the new orchestrator
        # TODO: Move import to top if circular dependency is resolved
        from .orchestrator import run_hallway
        final_output = await run_hallway(ctx)

        # Convert to legacy format for backward compatibility
        return self._convert_to_legacy_format(final_output, session_state_ref)

    def _convert_to_legacy_format(self, final_output, session_state_ref: str) -> Dict[str, Any]:
        """Convert new orchestrator output to legacy format."""
        return {
            "room_id": "hallway",
            "title": "Hallway",
            "version": "0.2.0",
            "purpose": "Deterministic multi-room session orchestrator",
            "stone_alignment": self.contract.get("stone_alignment", []),
            "sequence": self.sequence,
            "mini_walk_supported": self.contract.get("mini_walk_supported", False),
            "gate_profile": self.gate_profile,
            "inputs": {
                "session_state_ref": session_state_ref,
                "payloads": {},
                "options": {}
            },
            "outputs": final_output.outputs
        }

    def _determine_rooms_to_run(self, rooms_subset: List[str], mini_walk: bool) -> List[str]:
        """Determine which rooms to run based on options."""
        from .planner import plan_rooms

        if rooms_subset:
            # Validate that all requested rooms are in the sequence
            for room_id in rooms_subset:
                if room_id not in self.sequence:
                    raise ValueError(f"Room '{room_id}' not found in canonical sequence")

        return plan_rooms(self.sequence, rooms_subset, mini_walk)

    async def _run_room(self, room_id: str, session_state_ref: str, payloads: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Run a single room and return its output."""
        # Get the room function from registry
        try:
            room_fn = get_room_function(room_id)
        except KeyError as e:
            raise KeyError(f"Room '{room_id}' not found in registry: {e}")

        # Prepare input for the room
        room_input = {
            "session_state_ref": session_state_ref,
            "payload": payloads.get(room_id) if payloads else None,
            "options": {}  # Room-specific options can be added here
        }

        # Record start time for timing metadata
        start_time = time.time()

        try:
            # Run the room function (handle both async and sync)
            import asyncio
            if asyncio.iscoroutinefunction(room_fn):
                result = await room_fn(room_input)
            else:
                result = room_fn(room_input)

            # Record end time and compute elapsed time
            end_time = time.time()
            elapsed_ms = int((end_time - start_time) * 1000)

            # Add timing metadata to the result (non-user-facing)
            if isinstance(result, dict):
                result["_timing"] = {
                    "elapsed_ms": elapsed_ms,
                    "start_time": start_time,
                    "end_time": end_time
                }

            return result

        except Exception as e:
            # Record end time for failed executions
            end_time = time.time()
            elapsed_ms = int((end_time - start_time) * 1000)

            # Return error output with timing metadata
            return {
                "error": f"Room execution failed: {str(e)}",
                "room_id": room_id,
                "_timing": {
                    "elapsed_ms": elapsed_ms,
                    "start_time": start_time,
                    "end_time": end_time
                }
            }



    def _build_exit_summary(self, completed: bool, decline: Optional[Dict[str, Any]], steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build the exit summary for the hallway output."""
        return {
            "completed": completed,
            "decline": decline,
            "auditable_hash_chain": build_audit_chain(steps)
        }

    def _build_hallway_output(self, steps: List[Dict[str, Any]], final_state_ref: str, exit_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Build the final hallway output that validates against the v0.2 contract."""
        # Ensure session_state_ref is valid (non-empty)
        valid_session_ref = final_state_ref if final_state_ref and final_state_ref.strip() else "invalid-session-ref"

        return {
            "room_id": "hallway",
            "title": "Hallway",
            "version": "0.2.0",
            "purpose": "Deterministic multi-room session orchestrator",
            "stone_alignment": self.contract.get("stone_alignment", []),
            "sequence": self.sequence,
            "mini_walk_supported": self.contract.get("mini_walk_supported", False),
            "gate_profile": self.gate_profile,
            "inputs": {
                "session_state_ref": valid_session_ref,
                "payloads": {},
                "options": {}
            },
            "outputs": {
                "contract_version": "0.2.0",
                "steps": steps,
                "final_state_ref": valid_session_ref,
                "exit_summary": exit_summary
            }
        }


# Convenience function for external use
async def run_hallway(
    session_state_ref: str,
    payloads: Optional[Dict[str, Any]] = None,
    options: Optional[Dict[str, Any]] = None,
    contract: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function to run the hallway protocol.

    Args:
        session_state_ref: Reference to the session state
        payloads: Optional per-room payload map keyed by room_id
        options: Optional configuration options
        contract: Optional hallway contract (uses default if not provided)

    Returns:
        Dict that validates against the Hallway v0.2 contract
    """
    if contract is None:
        # Load default contract
        import json
        import os
        contract_path = os.path.join(os.path.dirname(__file__), "config", "hallway.contract.json")
        with open(contract_path, 'r') as f:
            contract = json.load(f)

    orchestrator = HallwayOrchestrator(contract)
    return await orchestrator.run(session_state_ref, payloads, options)
