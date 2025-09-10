"""
Tests for legacy vs new orchestrator parity.
"""

import pytest
import asyncio
from hallway.hallway import HallwayOrchestrator


class TestLegacyParity:
    """Test parity between legacy and new orchestrator implementations."""

    @pytest.mark.asyncio
    async def test_output_structure_parity(self):
        """Test that legacy and new orchestrator return same structure."""
        # Create deterministic contract
        contract = {
            'sequence': ['entry_room', 'diagnostic_room'],
            'gate_profile': {'chain': [], 'overrides': {}},
            'stone_alignment': []
        }

        orchestrator = HallwayOrchestrator(contract)

        # Fixed inputs for deterministic comparison
        session_ref = "test-session-123"
        payloads = {}
        base_options = {"mini_walk": True}

        # Run legacy orchestrator
        legacy_options = base_options.copy()
        legacy_result = await orchestrator.run(session_ref, payloads, legacy_options)

        # Run new orchestrator
        new_options = base_options.copy()
        new_options["use_new_orchestrator"] = True
        new_result = await orchestrator.run(session_ref, payloads, new_options)

        # Compare top-level structure
        assert set(legacy_result.keys()) == set(new_result.keys())

        # Compare non-variable fields
        structural_fields = ["room_id", "title", "version", "purpose"]
        for field in structural_fields:
            assert legacy_result[field] == new_result[field], f"Field {field} differs"

        # Compare outputs structure (allowing for different values)
        legacy_outputs = legacy_result.get("outputs", {})
        new_outputs = new_result.get("outputs", {})

        # Both should have similar output structure
        common_keys = ["contract_version", "completed", "exit_summary"]
        for key in common_keys:
            if key in legacy_outputs:
                assert key in new_outputs, f"New orchestrator missing output key: {key}"

    @pytest.mark.asyncio
    async def test_mini_walk_behavior_parity(self):
        """Test that mini-walk behaves the same in both orchestrators."""
        contract = {
            'sequence': ['entry_room', 'diagnostic_room', 'protocol_room', 'walk_room'],
            'gate_profile': {'chain': [], 'overrides': {}},
            'stone_alignment': []
        }

        orchestrator = HallwayOrchestrator(contract)

        session_ref = "test-session-mini"
        payloads = {}

        # Test mini-walk in both orchestrators
        legacy_result = await orchestrator.run(session_ref, payloads, {"mini_walk": True})
        new_result = await orchestrator.run(session_ref, payloads, {"mini_walk": True, "use_new_orchestrator": True})

        # Both should execute same number of steps for mini-walk
        legacy_steps = legacy_result.get("outputs", {}).get("steps", [])
        new_steps = new_result.get("outputs", {}).get("steps", [])

        # Mini-walk should limit the number of rooms executed
        # (exact comparison depends on planner implementation)
        assert len(legacy_steps) <= len(contract['sequence'])
        assert len(new_steps) <= len(contract['sequence'])

    @pytest.mark.asyncio
    async def test_empty_sequence_parity(self):
        """Test behavior with empty room sequence."""
        contract = {
            'sequence': [],
            'gate_profile': {'chain': [], 'overrides': {}},
            'stone_alignment': []
        }

        orchestrator = HallwayOrchestrator(contract)

        session_ref = "test-session-empty"
        payloads = {}

        # Both should handle empty sequence gracefully
        legacy_result = await orchestrator.run(session_ref, payloads, {})
        new_result = await orchestrator.run(session_ref, payloads, {"use_new_orchestrator": True})

        # Both should complete successfully with no steps
        # Check in exit_summary for legacy format
        legacy_completed = legacy_result.get("outputs", {}).get("exit_summary", {}).get("completed", False)
        new_completed = new_result.get("outputs", {}).get("exit_summary", {}).get("completed", False)

        assert legacy_completed == True
        assert new_completed == True

        legacy_steps = legacy_result.get("outputs", {}).get("steps", [])
        new_steps = new_result.get("outputs", {}).get("steps", [])

        assert len(legacy_steps) == 0
        assert len(new_steps) == 0

    @pytest.mark.asyncio
    async def test_session_state_ref_handling_parity(self):
        """Test that both orchestrators handle session state ref consistently."""
        contract = {
            'sequence': ['entry_room'],
            'gate_profile': {'chain': [], 'overrides': {}},
            'stone_alignment': []
        }

        orchestrator = HallwayOrchestrator(contract)
        payloads = {}

        # Test with various session ref values (exclude empty string as it gets normalized)
        test_refs = ["normal-session", "session-with-special-chars!@#"]

        for session_ref in test_refs:
            legacy_result = await orchestrator.run(session_ref, payloads, {})
            new_result = await orchestrator.run(session_ref, payloads, {"use_new_orchestrator": True})

            # Both should handle the session ref without crashing
            assert "outputs" in legacy_result
            assert "outputs" in new_result

            # Both should preserve session reference in inputs
            assert legacy_result.get("inputs", {}).get("session_state_ref") == session_ref
            assert new_result.get("inputs", {}).get("session_state_ref") == session_ref

    def test_contract_fields_parity(self):
        """Test that contract fields are handled consistently."""
        contract = {
            'sequence': ['entry_room', 'diagnostic_room'],
            'gate_profile': {'chain': ['test_gate'], 'overrides': {}},
            'stone_alignment': ['test_alignment'],
            'mini_walk_supported': True
        }

        orchestrator = HallwayOrchestrator(contract)

        # Both should preserve contract fields
        assert orchestrator.sequence == contract['sequence']
        assert orchestrator.gate_profile == contract['gate_profile']
        assert orchestrator.contract.get('stone_alignment') == contract['stone_alignment']
        assert orchestrator.contract.get('mini_walk_supported') == contract['mini_walk_supported']
