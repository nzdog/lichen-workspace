"""
Tests for policy enforcement and budget management.
"""

import pytest
from unittest.mock import Mock
from hallway.types import ExecutionContext, StepStatus
from hallway.orchestrator import run_hallway, _exceeded_budgets
from hallway.adapters.mock_adapters import MockLLM, MockVectorStore, MockClock, MockIdFactory, MockMetrics, MockLogger
from hallway.adapters.fs_storage import FilesystemStorage
from hallway.adapters.ports_builder import PortsImpl
from hallway.gates import CoherenceGate, GateDecision


class TestPolicyBudget:
    """Test policy enforcement and budget management."""

    def test_budget_exceeded_tokens(self):
        """Test budget enforcement for token limit."""
        ctx = ExecutionContext(
            run_id="test-1",
            correlation_id="test-corr-1",
            rooms_to_run=["entry_room"],
            state={"session_state_ref": "test-session"},
            budgets={"tokens": 100.0, "time_ms": 5000.0, "retries": 3.0},
            usage={"tokens": 150.0, "time_ms": 1000.0, "retries": 0.0},  # Tokens exceeded
            ports=Mock(),
            policy={"stop_on_decline": True}
        )

        assert _exceeded_budgets(ctx) is True

    def test_budget_exceeded_time(self):
        """Test budget enforcement for time limit."""
        ctx = ExecutionContext(
            run_id="test-1",
            correlation_id="test-corr-1",
            rooms_to_run=["entry_room"],
            state={"session_state_ref": "test-session"},
            budgets={"tokens": 100.0, "time_ms": 5000.0, "retries": 3.0},
            usage={"tokens": 50.0, "time_ms": 6000.0, "retries": 0.0},  # Time exceeded
            ports=Mock(),
            policy={"stop_on_decline": True}
        )

        assert _exceeded_budgets(ctx) is True

    def test_budget_not_exceeded(self):
        """Test budget enforcement when limits are not exceeded."""
        ctx = ExecutionContext(
            run_id="test-1",
            correlation_id="test-corr-1",
            rooms_to_run=["entry_room"],
            state={"session_state_ref": "test-session"},
            budgets={"tokens": 100.0, "time_ms": 5000.0, "retries": 3.0},
            usage={"tokens": 50.0, "time_ms": 2000.0, "retries": 1.0},  # All within limits
            ports=Mock(),
            policy={"stop_on_decline": True}
        )

        assert _exceeded_budgets(ctx) is False

    @pytest.mark.asyncio
    async def test_budget_stop_orchestrator(self):
        """Test orchestrator halts when budget is exceeded."""
        # Create a declining gate to trigger budget usage
        class BudgetConsumingGate(CoherenceGate):
            def evaluate(self, room_id, session_state_ref, payload=None):
                return GateDecision("budget_gate", False, "consuming budget")

        ports = PortsImpl(
            llm=MockLLM(),
            vec=MockVectorStore(),
            store=FilesystemStorage("/tmp/test"),
            clock=MockClock(),
            ids=MockIdFactory(),
            metrics=MockMetrics(),
            log=MockLogger()
        )

        ctx = ExecutionContext(
            run_id="test-budget-1",
            correlation_id="test-corr-1",
            rooms_to_run=["entry_room", "diagnostic_room"],
            state={"session_state_ref": "test-session", "payloads": {}},
            budgets={"tokens": 1.0, "time_ms": 1.0, "retries": 1.0},  # Very small budgets
            usage={"tokens": 2.0, "time_ms": 2.0, "retries": 0.0},  # Already exceeded
            ports=ports,
            policy={
                "stop_on_decline": True,
                "gate_profile": {"chain": [], "overrides": {}},
                "gates": {},
                "max_retries": 3
            }
        )

        result = await run_hallway(ctx)

        # Should halt due to budget exceeded
        budget_events = [e for e in result.events if e.get("reason") == "budget_exceeded"]
        assert len(budget_events) > 0

    @pytest.mark.asyncio
    async def test_decline_stop_policy_true(self):
        """Test orchestrator stops when decline occurs and stop_on_decline=True."""
        # Create a declining gate
        class DecliningGate(CoherenceGate):
            def evaluate(self, room_id, session_state_ref, payload=None):
                return GateDecision("declining_gate", False, "test decline")

        ports = PortsImpl(
            llm=MockLLM(),
            vec=MockVectorStore(),
            store=FilesystemStorage("/tmp/test"),
            clock=MockClock(),
            ids=MockIdFactory(),
            metrics=MockMetrics(),
            log=MockLogger()
        )

        ctx = ExecutionContext(
            run_id="test-decline-1",
            correlation_id="test-corr-1",
            rooms_to_run=["entry_room", "diagnostic_room"],
            state={"session_state_ref": "test-session", "payloads": {}},
            budgets={"tokens": 1000.0, "time_ms": 10000.0, "retries": 5.0},
            usage={"tokens": 0.0, "time_ms": 0.0, "retries": 0.0},
            ports=ports,
            policy={
                "stop_on_decline": True,  # Should stop on decline
                "gate_profile": {"chain": ["declining_gate"], "overrides": {}},
                "gates": {"declining_gate": DecliningGate()},
                "max_retries": 3
            }
        )

        result = await run_hallway(ctx)

        # Should halt due to gate decline
        halt_events = [e for e in result.events if e.get("phase") == "halt"]
        assert len(halt_events) > 0

        # Should have halt_reason in the event
        halt_event = halt_events[0]
        assert "halt_reason" in halt_event or "reason" in halt_event

    @pytest.mark.asyncio
    async def test_decline_stop_policy_false(self):
        """Test orchestrator continues when decline occurs and stop_on_decline=False."""
        # Create a declining gate
        class DecliningGate(CoherenceGate):
            def evaluate(self, room_id, session_state_ref, payload=None):
                return GateDecision("declining_gate", False, "test decline")

        ports = PortsImpl(
            llm=MockLLM(),
            vec=MockVectorStore(),
            store=FilesystemStorage("/tmp/test"),
            clock=MockClock(),
            ids=MockIdFactory(),
            metrics=MockMetrics(),
            log=MockLogger()
        )

        ctx = ExecutionContext(
            run_id="test-decline-continue-1",
            correlation_id="test-corr-1",
            rooms_to_run=["entry_room"],  # Just one room to test continue behavior
            state={"session_state_ref": "test-session", "payloads": {}},
            budgets={"tokens": 1000.0, "time_ms": 10000.0, "retries": 5.0},
            usage={"tokens": 0.0, "time_ms": 0.0, "retries": 0.0},
            ports=ports,
            policy={
                "stop_on_decline": False,  # Should continue on decline
                "gate_profile": {"chain": ["declining_gate"], "overrides": {}},
                "gates": {"declining_gate": DecliningGate()},
                "max_retries": 3
            }
        )

        result = await run_hallway(ctx)

        # Should have decline_continue events instead of halt
        continue_events = [e for e in result.events if e.get("phase") == "decline_continue"]
        assert len(continue_events) > 0
