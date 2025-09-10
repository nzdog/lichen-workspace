"""
Test hallway decline path
Verifies gate deny behavior and early short-circuit functionality
"""

import pytest
import json
import os
from jsonschema import validate
from hallway.hallway import HallwayOrchestrator
from hallway.gates import GateInterface, GateDecision


class MockDenyingGate(GateInterface):
    """Mock gate that denies specific rooms for testing"""
    
    def __init__(self, deny_rooms=None):
        self.deny_rooms = deny_rooms or []
    
    def evaluate(self, room_id: str, session_state_ref: str, payload: dict = None) -> GateDecision:
        if room_id in self.deny_rooms:
            return GateDecision(
                gate="mock_denying_gate",
                allow=False,
                reason=f"Room {room_id} is denied for testing",
                details={"room_id": room_id, "test_mode": True}
            )
        
        return GateDecision(
            gate="mock_denying_gate",
            allow=True,
            reason="Room allowed",
            details={"room_id": room_id, "test_mode": True}
        )


class TestHallwayDeclinePath:
    """Test hallway decline path execution"""
    
    @classmethod
    def setup_class(cls):
        """Load the hallway contract and schema for testing"""
        # Load contract
        contract_path = os.path.join(os.path.dirname(__file__), "..", "config", "hallway.contract.json")
        with open(contract_path, 'r') as f:
            cls.contract = json.load(f)
        
        # Load schema
        schema_path = os.path.join(os.path.dirname(__file__), "..", "schemas", "hallway_v0_2.schema.json")
        with open(schema_path, 'r') as f:
            cls.schema = json.load(f)
    
    @pytest.mark.asyncio
    async def test_gate_deny_early_short_circuit(self):
        """Test that gate deny causes early short-circuit when stop_on_decline=True"""
        # Configure gate to deny the second room
        deny_gate = MockDenyingGate(deny_rooms=["diagnostic_room"])
        gates = {"coherence_gate": deny_gate}
        
        orchestrator = HallwayOrchestrator(self.contract, gates)
        
        # Run with stop_on_decline=True (default)
        result = await orchestrator.run(
            session_state_ref="test-session-gate-deny",
            options={"stop_on_decline": True},
            payloads={
                "entry_room": {"consent": "YES"}
            }
        )
        
        # Validate against schema
        validate(instance=result, schema=self.schema)
        
        # Should have two steps: entry_room (success) and diagnostic_room (gate denied)
        assert len(result["outputs"]["steps"]) == 2
        
        # First step should be ok
        first_step = result["outputs"]["steps"][0]
        assert first_step["room_id"] == "entry_room"
        assert first_step["status"] == "ok"
        
        # Second step should be decline due to gate
        second_step = result["outputs"]["steps"][1]
        assert second_step["room_id"] == "diagnostic_room"
        assert second_step["status"] == "decline"
        
        # Exit summary should indicate not completed
        exit_summary = result["outputs"]["exit_summary"]
        assert exit_summary["completed"] is False
        assert exit_summary["decline"] is not None
        assert exit_summary["decline"]["reason"] == "gate_chain_failed"
        
        # Hash chain should have two hashes
        assert len(exit_summary["auditable_hash_chain"]) == 2
    
    @pytest.mark.asyncio
    async def test_gate_deny_continue_when_stop_on_decline_false(self):
        """Test that gate deny doesn't stop execution when stop_on_decline=False"""
        # Configure gate to deny the second room
        deny_gate = MockDenyingGate(deny_rooms=["diagnostic_room"])
        gates = {"coherence_gate": deny_gate}
        
        orchestrator = HallwayOrchestrator(self.contract, gates)
        
        # Run with stop_on_decline=False
        result = await orchestrator.run(
            session_state_ref="test-session-gate-deny-continue",
            options={"stop_on_decline": False},
            payloads={
                "entry_room": {"consent": "YES"}
            }
        )
        
        # Validate against schema
        validate(instance=result, schema=self.schema)
        
        # Should have all steps
        expected_rooms = [
            "entry_room",
            "diagnostic_room",
            "protocol_room",
            "walk_room",
            "memory_room",
            "integration_commit_room",
            "exit_room"
        ]
        
        assert len(result["outputs"]["steps"]) == len(expected_rooms)
        
        # First step should be ok
        first_step = result["outputs"]["steps"][0]
        assert first_step["room_id"] == "entry_room"
        assert first_step["status"] == "ok"
        
        # Second step should be decline due to gate
        second_step = result["outputs"]["steps"][1]
        assert second_step["room_id"] == "diagnostic_room"
        assert second_step["status"] == "decline"
        
        # Exit summary should indicate completed (since we didn't stop on decline)
        exit_summary = result["outputs"]["exit_summary"]
        assert exit_summary["completed"] is True
        assert exit_summary["decline"] is None
        
        # Hash chain should have all hashes
        assert len(exit_summary["auditable_hash_chain"]) == len(expected_rooms)
    
    @pytest.mark.asyncio
    async def test_room_decline_early_short_circuit(self):
        """Test that room decline causes early short-circuit when stop_on_decline=True"""
        orchestrator = HallwayOrchestrator(self.contract)
        
        # Mock a room that will decline by creating a custom gate that always denies
        class AlwaysDenyGate(GateInterface):
            def evaluate(self, room_id: str, session_state_ref: str, payload: dict = None) -> GateDecision:
                return GateDecision(
                    gate="always_deny_gate",
                    allow=False,
                    reason="Always denied for testing",
                    details={"room_id": room_id, "test_mode": True}
                )
        
        gates = {"coherence_gate": AlwaysDenyGate()}
        orchestrator.gates = gates
        
        # Run with stop_on_decline=True
        result = await orchestrator.run(
            session_state_ref="test-session-room-decline",
            options={"stop_on_decline": True}
        )
        
        # Validate against schema
        validate(instance=result, schema=self.schema)
        
        # Should have only one step before gate denied
        assert len(result["outputs"]["steps"]) == 1
        
        # First step should be decline
        first_step = result["outputs"]["steps"][0]
        assert first_step["status"] == "decline"
        
        # Exit summary should indicate not completed
        exit_summary = result["outputs"]["exit_summary"]
        assert exit_summary["completed"] is False
        assert exit_summary["decline"] is not None
        assert exit_summary["decline"]["reason"] == "gate_chain_failed"
    
    @pytest.mark.asyncio
    async def test_invalid_room_id_validation(self):
        """Test that invalid room_id in rooms_subset causes validation error"""
        orchestrator = HallwayOrchestrator(self.contract)
        
        # Try to run with invalid room_id
        with pytest.raises(ValueError, match="Room 'invalid_room' not found in canonical sequence"):
            await orchestrator.run(
                session_state_ref="test-session-invalid-room",
                options={"rooms_subset": ["entry_room", "invalid_room", "exit_room"]}
            )
    
    @pytest.mark.asyncio
    async def test_empty_session_state_ref_gate_deny(self):
        """Test that empty session_state_ref causes gate deny"""
        orchestrator = HallwayOrchestrator(self.contract)
        
        # Run with empty session_state_ref
        result = await orchestrator.run(
            session_state_ref="",  # Empty string
            options={"stop_on_decline": True}
        )
        
        # Validate against schema
        validate(instance=result, schema=self.schema)
        
        # Should have only one step before gate denied
        assert len(result["outputs"]["steps"]) == 1
        
        # First step should be decline
        first_step = result["outputs"]["steps"][0]
        assert first_step["room_id"] == "entry_room"
        assert first_step["status"] == "decline"
        
        # Exit summary should indicate not completed
        exit_summary = result["outputs"]["exit_summary"]
        assert exit_summary["completed"] is False
        assert exit_summary["decline"] is not None
        assert exit_summary["decline"]["reason"] == "gate_chain_failed"
    
    @pytest.mark.asyncio
    async def test_unknown_gate_in_chain(self):
        """Test that unknown gate in chain causes deny by default"""
        # Create contract with unknown gate
        contract_with_unknown_gate = self.contract.copy()
        contract_with_unknown_gate["gate_profile"]["chain"] = ["unknown_gate"]
        
        orchestrator = HallwayOrchestrator(contract_with_unknown_gate)
        
        # Run with stop_on_decline=True
        result = await orchestrator.run(
            session_state_ref="test-session-unknown-gate",
            options={"stop_on_decline": True}
        )
        
        # Validate against schema
        validate(instance=result, schema=self.schema)
        
        # Should have only one step before gate denied
        assert len(result["outputs"]["steps"]) == 1
        
        # First step should be decline
        first_step = result["outputs"]["steps"][0]
        assert first_step["room_id"] == "entry_room"
        assert first_step["status"] == "decline"
        
        # Check that gate decision shows unknown gate
        gate_decisions = first_step["gate_decisions"]
        assert len(gate_decisions) == 1
        assert gate_decisions[0]["gate"] == "unknown_gate"
        assert gate_decisions[0]["allow"] is False
        assert "not found in available gates" in gate_decisions[0]["reason"]
        
        # Exit summary should indicate not completed
        exit_summary = result["outputs"]["exit_summary"]
        assert exit_summary["completed"] is False
        assert exit_summary["decline"] is not None
        assert exit_summary["decline"]["reason"] == "gate_chain_failed"
    
    @pytest.mark.asyncio
    async def test_gate_chain_evaluation_order(self):
        """Test that gate chain is evaluated in order and short-circuits on first deny"""
        # Create a gate that counts evaluations
        class CountingGate(GateInterface):
            def __init__(self):
                self.evaluation_count = 0
                self.evaluated_rooms = []
            
            def evaluate(self, room_id: str, session_state_ref: str, payload: dict = None) -> GateDecision:
                self.evaluation_count += 1
                self.evaluated_rooms.append(room_id)
                
                # Deny on third evaluation
                if self.evaluation_count == 3:
                    return GateDecision(
                        gate="counting_gate",
                        allow=False,
                        reason="Third evaluation denied",
                        details={"evaluation_count": self.evaluation_count}
                    )
                
                return GateDecision(
                    gate="counting_gate",
                    allow=True,
                    reason="Evaluation allowed",
                    details={"evaluation_count": self.evaluation_count}
                )
        
        # Use a fresh copy of the contract to avoid interference from other tests
        contract_copy = self.contract.copy()
        # Modify the contract to use our counting gate
        contract_copy["gate_profile"]["chain"] = ["counting_gate"]
        gates = {"counting_gate": CountingGate()}
        orchestrator = HallwayOrchestrator(contract_copy, gates)
        
        # Run with stop_on_decline=True
        result = await orchestrator.run(
            session_state_ref="test-session-gate-order",
            options={"stop_on_decline": True},
            payloads={
                "entry_room": {"consent": "YES"},
                "exit_room": {
                    "completion_confirmed": True,
                    "session_goals_met": True
                }
            }
        )
        
        # Validate against schema
        validate(instance=result, schema=self.schema)
        
        # Should have exactly 3 steps before gate denied
        assert len(result["outputs"]["steps"]) == 3
        
        # Check that rooms were evaluated in order
        expected_rooms = ["entry_room", "diagnostic_room", "protocol_room"]
        for i, step in enumerate(result["outputs"]["steps"]):
            assert step["room_id"] == expected_rooms[i]
        
        # Third step should be decline
        third_step = result["outputs"]["steps"][2]
        assert third_step["room_id"] == "protocol_room"
        assert third_step["status"] == "decline"
        
        # Exit summary should indicate not completed
        exit_summary = result["outputs"]["exit_summary"]
        assert exit_summary["completed"] is False
        assert exit_summary["decline"] is not None
        assert exit_summary["decline"]["reason"] == "gate_chain_failed"


if __name__ == "__main__":
    pytest.main([__file__])
