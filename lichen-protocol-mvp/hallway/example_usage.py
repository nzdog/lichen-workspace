"""
Example usage of the Hallway Protocol
Demonstrates how to use the HallwayOrchestrator for different scenarios
"""

import asyncio
import json
from hallway import HallwayOrchestrator, run_hallway


async def example_full_walk():
    """Example: Run the full canonical sequence"""
    print("=== Full Canonical Walk Example ===")

    # Load the default contract
    with open("hallway/config/hallway.contract.json", "r") as f:
        contract = json.load(f)

    # Create orchestrator
    orchestrator = HallwayOrchestrator(contract)

    # Run full sequence with explicit consent
    result = await orchestrator.run(
        session_state_ref="example-session-full",
        payloads={
            "entry_room": {"user_input": "Hello, I want to start a session", "consent": "YES"},
            "protocol_room": {"protocol_type": "standard"}
        }
    )

    print(f"Completed: {result['outputs']['exit_summary']['completed']}")
    print(f"Steps executed: {len(result['outputs']['steps'])}")
    print(f"Final state ref: {result['outputs']['final_state_ref']}")

    return result


async def example_mini_walk():
    """Example: Run a mini-walk (first three rooms or fewer)"""
    print("\n=== Mini Walk Example ===")

    # Use the convenience function with explicit consent
    result = await run_hallway(
        session_state_ref="example-session-mini",
        options={"mini_walk": True},
        payloads={
            "entry_room": {"consent": "YES"}
        }
    )

    print(f"Completed: {result['outputs']['exit_summary']['completed']}")
    print(f"Steps executed: {len(result['outputs']['steps'])}")

    # Show which rooms were run
    rooms_run = [step["room_id"] for step in result["outputs"]["steps"]]
    print(f"Rooms run: {rooms_run}")

    return result


async def example_custom_subset():
    """Example: Run a custom subset of rooms"""
    print("\n=== Custom Subset Example ===")

    result = await run_hallway(
        session_state_ref="example-session-custom",
        options={"rooms_subset": ["entry_room", "protocol_room", "exit_room"]},
        payloads={
            "entry_room": {"consent": "YES"}
        }
    )

    print(f"Completed: {result['outputs']['exit_summary']['completed']}")
    print(f"Steps executed: {len(result['outputs']['steps'])}")

    # Show which rooms were run
    rooms_run = [step["room_id"] for step in result["outputs"]["steps"]]
    print(f"Rooms run: {rooms_run}")

    return result


async def example_dry_run():
    """Example: Run a dry run without executing actual rooms"""
    print("\n=== Dry Run Example ===")

    result = await run_hallway(
        session_state_ref="example-session-dry",
        options={"dry_run": True}
    )

    print(f"Completed: {result['outputs']['exit_summary']['completed']}")
    print(f"Steps executed: {len(result['outputs']['steps'])}")

    # Show that it's a dry run
    for step in result["outputs"]["steps"]:
        print(f"  {step['room_id']}: {step['data']['dry_run']}")

    return result


async def example_gate_deny():
    """Example: Demonstrate gate deny behavior"""
    print("\n=== Gate Deny Example ===")

    # Create a contract with a gate that will deny
    contract = {
        "room_id": "hallway",
        "title": "Hallway",
        "version": "0.2.0",
        "purpose": "Deterministic multi-room session orchestrator",
        "stone_alignment": ["deterministic", "atomic", "auditable"],
        "sequence": ["entry_room", "diagnostic_room", "exit_room"],
        "mini_walk_supported": True,
        "gate_profile": {
            "chain": ["coherence_gate"],
            "overrides": {}
        }
    }

    # Create orchestrator with custom gate that denies diagnostic_room
    from hallway.gates import GateInterface, GateDecision

    class DenyDiagnosticGate(GateInterface):
        def evaluate(self, room_id: str, session_state_ref: str, payload: dict = None) -> GateDecision:
            if room_id == "diagnostic_room":
                return GateDecision(
                    gate="deny_diagnostic_gate",
                    allow=False,
                    reason="Diagnostic room is disabled for this example",
                    details={"room_id": room_id}
                )
            return GateDecision(
                gate="deny_diagnostic_gate",
                allow=True,
                reason="Room allowed",
                details={"room_id": room_id}
            )

    gates = {"coherence_gate": DenyDiagnosticGate()}
    orchestrator = HallwayOrchestrator(contract, gates)

    # Run with stop_on_decline=True (default)
    result = await orchestrator.run(
        session_state_ref="example-session-gate-deny",
        options={"stop_on_decline": True}
    )

    print(f"Completed: {result['outputs']['exit_summary']['completed']}")
    print(f"Steps executed: {len(result['outputs']['steps'])}")

    # Show the decline reason
    if result['outputs']['exit_summary']['decline']:
        print(f"Decline reason: {result['outputs']['exit_summary']['decline']['reason']}")

    return result


async def main():
    """Run all examples"""
    try:
        # Run examples
        await example_full_walk()
        await example_mini_walk()
        await example_custom_subset()
        await example_dry_run()
        await example_gate_deny()

        print("\n=== All Examples Completed Successfully ===")

    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
