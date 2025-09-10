#!/usr/bin/env python3
"""
Lichen Protocol SIS MVP Demo Runner

A comprehensive demo experience showcasing the end-to-end hallway orchestrator
with prepared scenarios that demonstrate the Foundation Stones:
- Light Before Form
- Speed of Trust  
- Presence Is Productivity
- Integrity Is the Growth Strategy
"""

import asyncio
import json
import sys
from typing import Dict, Any, List
from hallway import HallwayOrchestrator, run_hallway


class LichenDemo:
    """Main demo orchestrator for showcasing the Lichen Protocol SIS MVP"""
    
    def __init__(self):
        self.contract = self._load_contract()
        self.orchestrator = HallwayOrchestrator(self.contract)
    
    def _load_contract(self) -> Dict[str, Any]:
        """Load the canonical hallway contract"""
        try:
            with open("hallway/config/hallway.contract.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print("❌ Error: Could not find hallway contract file")
            print("   Make sure you're running from the repo root directory")
            sys.exit(1)
    
    def _print_header(self, title: str):
        """Print a formatted header for demo sections"""
        print(f"\n{'='*60}")
        print(f"🧬 {title}")
        print(f"{'='*60}")
    
    def _print_step(self, step: Dict[str, Any], step_num: int):
        """Print formatted step information"""
        room_id = step["room_id"]
        status = step["status"]
        display_text = step["data"].get("display_text", "No display text available")
        next_action = step["data"].get("next_action", "unknown")
        
        # Truncate display text for demo readability
        if len(display_text) > 200:
            display_text = display_text[:200] + "..."
        
        status_emoji = "✅" if status == "ok" else "❌"
        print(f"\n{status_emoji} Step {step_num}: {room_id}")
        print(f"   Action: {next_action}")
        print(f"   Output: {display_text}")
        
        if status == "decline":
            decline_reason = step["decline"]["reason"]
            print(f"   ⚠️  Decline: {decline_reason}")
    
    def _print_summary(self, result: Dict[str, Any]):
        """Print demo summary"""
        exit_summary = result["outputs"]["exit_summary"]
        completed = exit_summary["completed"]
        steps = result["outputs"]["steps"]
        
        print(f"\n{'='*60}")
        print(f"📊 DEMO SUMMARY")
        print(f"{'='*60}")
        print(f"Completed: {'✅ Yes' if completed else '❌ No'}")
        print(f"Steps executed: {len(steps)}")
        print(f"Final state ref: {result['outputs']['final_state_ref']}")
        
        if not completed and exit_summary.get("decline"):
            decline = exit_summary["decline"]
            print(f"Decline reason: {decline['reason']}")
        
        # Show Foundation Stones demonstration
        print(f"\n🏛️  Foundation Stones Demonstrated:")
        if completed:
            print(f"   • Light Before Form: Structured, predictable flow")
            print(f"   • Speed of Trust: Efficient room-to-room transitions")
            print(f"   • Presence Is Productivity: Focused, purposeful execution")
            print(f"   • Integrity Is the Growth Strategy: Validated, auditable results")
        else:
            print(f"   • Integrity Is the Growth Strategy: Proper decline handling")
    
    async def run_full_canonical_walk(self):
        """Run the complete 7-step canonical sequence"""
        self._print_header("Full Canonical Walk (7 Steps)")
        print("Demonstrating the complete Lichen Protocol journey:")
        print("Entry → Diagnostic → Protocol → Walk → Memory → Integration → Exit")
        
        result = await self.orchestrator.run(
            session_state_ref="demo-full-canonical",
            options={"stop_on_decline": True},
            payloads={
                "entry_room": {"consent": "YES"},
                "diagnostic_room": {"tone": "focused", "residue": "clear"},
                "protocol_room": {"protocol_id": "clearing_entry", "depth": "full"},
                "walk_room": {
                    "protocol_id": "demo_walk",
                    "steps": [
                        {"title": "Demo Step 1", "description": "First demonstration step"},
                        {"title": "Demo Step 2", "description": "Second demonstration step"}
                    ]
                },
                "memory_room": {"tone_label": "focused", "action": "capture"},
                "integration_commit_room": {
                    "integration_notes": "Demo integration complete",
                    "session_context": "Full canonical walk demonstration"
                },
                "exit_room": {
                    "completion_confirmed": True,
                    "session_goals_met": True
                }
            }
        )
        
        for i, step in enumerate(result["outputs"]["steps"], 1):
            self._print_step(step, i)
        
        self._print_summary(result)
        return result
    
    async def run_mini_walk(self):
        """Run the mini walk (Entry → Exit)"""
        self._print_header("Mini Walk (Entry → Exit)")
        print("Demonstrating the essential entry and exit flow:")
        print("Entry → Exit")
        
        result = await run_hallway(
            session_state_ref="demo-mini-walk",
            options={"mini_walk": True},
            payloads={
                "entry_room": {"consent": "YES"},
                "exit_room": {
                    "completion_confirmed": True,
                    "session_goals_met": True
                }
            }
        )
        
        for i, step in enumerate(result["outputs"]["steps"], 1):
            self._print_step(step, i)
        
        self._print_summary(result)
        return result
    
    async def run_custom_subset(self):
        """Run a custom subset (Entry → Protocol → Exit)"""
        self._print_header("Custom Subset (Entry → Protocol → Exit)")
        print("Demonstrating a focused protocol exploration:")
        print("Entry → Protocol → Exit")
        
        result = await run_hallway(
            session_state_ref="demo-custom-subset",
            options={"rooms_subset": ["entry_room", "protocol_room", "exit_room"]},
            payloads={
                "entry_room": {"consent": "YES"},
                "protocol_room": {"protocol_id": "clearing_entry", "depth": "full"},
                "exit_room": {
                    "completion_confirmed": True,
                    "session_goals_met": True
                }
            }
        )
        
        for i, step in enumerate(result["outputs"]["steps"], 1):
            self._print_step(step, i)
        
        self._print_summary(result)
        return result
    
    async def run_dry_run(self):
        """Run a dry run to show all available rooms"""
        self._print_header("Dry Run (Availability Check)")
        print("Demonstrating all available rooms without execution:")
        
        result = await run_hallway(
            session_state_ref="demo-dry-run",
            options={"dry_run": True}
        )
        
        print(f"\n📋 Available Rooms ({len(result['outputs']['steps'])}):")
        for step in result["outputs"]["steps"]:
            room_id = step["room_id"]
            dry_run_status = step["data"]["dry_run"]
            status_emoji = "✅" if dry_run_status else "❌"
            print(f"   {status_emoji} {room_id}")
        
        self._print_summary(result)
        return result
    
    async def run_gate_deny(self):
        """Run a gate deny scenario to demonstrate governance"""
        self._print_header("Gate Deny (Governance Demonstration)")
        print("Demonstrating proper decline handling when gates deny access:")
        
        # Create a custom contract with a gate that will deny
        deny_contract = self.contract.copy()
        deny_contract["sequence"] = ["entry_room", "diagnostic_room", "exit_room"]
        
        # Create a gate that denies diagnostic_room
        from hallway.gates import GateInterface, GateDecision
        
        class DemoDenyGate(GateInterface):
            def evaluate(self, room_id: str, session_state_ref: str, payload: dict = None) -> GateDecision:
                if room_id == "diagnostic_room":
                    return GateDecision(
                        gate="demo_deny_gate",
                        allow=False,
                        reason="Demo: Diagnostic room disabled for governance demonstration",
                        details={"room_id": room_id, "demo": True}
                    )
                return GateDecision(
                    gate="demo_deny_gate",
                    allow=True,
                    reason="Demo: Room allowed",
                    details={"room_id": room_id, "demo": True}
                )
        
        deny_orchestrator = HallwayOrchestrator(deny_contract, {"coherence_gate": DemoDenyGate()})
        
        result = await deny_orchestrator.run(
            session_state_ref="demo-gate-deny",
            options={"stop_on_decline": True},
            payloads={
                "entry_room": {"consent": "YES"},
                "exit_room": {
                    "completion_confirmed": True,
                    "session_goals_met": True
                }
            }
        )
        
        for i, step in enumerate(result["outputs"]["steps"], 1):
            self._print_step(step, i)
        
        self._print_summary(result)
        return result
    
    async def run_scenario(self, scenario: str):
        """Run a specific scenario"""
        scenarios = {
            "1": ("Full Canonical Walk", self.run_full_canonical_walk),
            "2": ("Mini Walk", self.run_mini_walk),
            "3": ("Custom Subset", self.run_custom_subset),
            "4": ("Dry Run", self.run_dry_run),
            "5": ("Gate Deny", self.run_gate_deny),
        }
        
        if scenario not in scenarios:
            print(f"❌ Unknown scenario: {scenario}")
            return None
        
        scenario_name, scenario_func = scenarios[scenario]
        print(f"\n🚀 Starting {scenario_name}...")
        return await scenario_func()
    
    def show_menu(self):
        """Display the demo menu"""
        print(f"\n{'='*60}")
        print(f"🧬 LICHEN PROTOCOL SIS MVP DEMO")
        print(f"{'='*60}")
        print(f"Foundation Stones: Light Before Form, Speed of Trust,")
        print(f"Presence Is Productivity, Integrity Is the Growth Strategy")
        print(f"\nAvailable Scenarios:")
        print(f"  1. Full Canonical Walk (7 steps)")
        print(f"  2. Mini Walk (Entry → Exit)")
        print(f"  3. Custom Subset (Entry → Protocol → Exit)")
        print(f"  4. Dry Run (Availability Check)")
        print(f"  5. Gate Deny (Governance Demonstration)")
        print(f"  6. Run All Scenarios")
        print(f"  0. Exit")
        print(f"{'='*60}")


async def main():
    """Main demo entry point"""
    demo = LichenDemo()
    
    if len(sys.argv) > 1:
        # Command line argument provided
        scenario = sys.argv[1]
        if scenario == "all":
            print("🚀 Running all demo scenarios...")
            scenarios = ["1", "2", "3", "4", "5"]
            for scenario_num in scenarios:
                await demo.run_scenario(scenario_num)
                if scenario_num != "5":  # Don't pause after last scenario
                    input("\nPress Enter to continue to next scenario...")
        else:
            await demo.run_scenario(scenario)
    else:
        # Interactive mode
        while True:
            demo.show_menu()
            choice = input("\nSelect scenario (0-6): ").strip()
            
            if choice == "0":
                print("\n👋 Thank you for exploring the Lichen Protocol SIS MVP!")
                break
            elif choice == "6":
                print("🚀 Running all demo scenarios...")
                scenarios = ["1", "2", "3", "4", "5"]
                for scenario_num in scenarios:
                    await demo.run_scenario(scenario_num)
                    if scenario_num != "5":  # Don't pause after last scenario
                        input("\nPress Enter to continue to next scenario...")
            else:
                await demo.run_scenario(choice)
                input("\nPress Enter to return to menu...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted. Thank you for exploring the Lichen Protocol SIS MVP!")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        sys.exit(1)
