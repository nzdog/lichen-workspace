import types
import pytest

from hallway.hallway_types import ExecutionContext, StepStatus
from hallway.orchestrator import run_hallway
import hallway.orchestrator as orch_mod  # we patch the symbol used inside orchestrator


class FakeLog:
    def __init__(self):
        self.events = []
    def info(self, e):
        self.events.append(("info", e))
    def error(self, e):
        self.events.append(("error", e))


class FakeClock:
    def now_iso(self):
        return "2025-09-07T12:00:00Z"


class FakeIds:
    def new_id(self, prefix="run"):
        return f"{prefix}_abc123"


class FakeMetrics:
    def incr(self, name, **tags):
        pass
    def timing(self, name, ms, **tags):
        pass


class FakeVec:
    async def embed(self, texts):
        return [[0.0] * 3 for _ in texts]
    async def search(self, query_vec, k, filters=None):
        return []


class FakeStore:
    async def put_json(self, bucket, key, obj):
        return None
    async def get_json(self, bucket, key):
        return {}


class FakePorts:
    def __init__(self):
        self.log = FakeLog()
        self.clock = FakeClock()
        self.ids = FakeIds()
        self.metrics = FakeMetrics()
        self.vec = FakeVec()
        self.store = FakeStore()
        # llm is unused in these tests; provide a minimal stub
        self.llm = types.SimpleNamespace(complete=lambda *a, **k: "...")


def _ctx(run_id: str) -> ExecutionContext:
    return ExecutionContext(
        run_id=run_id,
        correlation_id=f"corr_{run_id}",
        rooms_to_run=["entry", "diagnostics", "protocol"],
        state={},
        budgets={"tokens": 1e9, "time_ms": 1e9, "retries": 5},
        ports=FakePorts(),
        policy={"stop_on_decline": True},
    )


@pytest.mark.asyncio
async def test_golden_path(monkeypatch):
    async def ok_step(room_id, ctx):
        return types.SimpleNamespace(
            status=StepStatus.OK,
            outputs={f"{room_id}_out": True},
            errors=[],
            metrics={},
        )
    # IMPORTANT: patch the symbol used inside orchestrator, not hallway.steps
    monkeypatch.setattr(orch_mod, "run_step", ok_step)

    final = await run_hallway(_ctx("r1"))

    # should have an 'end' event recorded
    events = [e for e in final.events if isinstance(e, dict)]
    assert any(e.get("phase") == "end" for e in events)

    # outputs may be merged into state rather than final.outputs; be tolerant
    merged = dict(final.outputs or {})
    assert "protocol_out" in merged


@pytest.mark.asyncio
async def test_halt_on_decline(monkeypatch):
    seen = []

    async def decline_first(room_id, ctx):
        seen.append(room_id)
        return types.SimpleNamespace(
            status=StepStatus.HALT,
            outputs={},
            errors=["declined_by_gate"],
            halt_reason="declined_by_gate",
            metrics={},
        )

    monkeypatch.setattr(orch_mod, "run_step", decline_first)

    final = await run_hallway(_ctx("r2"))

    # only first room attempted
    assert seen == ["entry"]

    # the orchestrator should log a HALT/declined reason
    assert any(
        isinstance(e, dict) and e.get("reason") == "step_halted"
        for e in final.events
    )
    # also check that the halt_reason is preserved in the event
    assert any(
        isinstance(e, dict) and e.get("halt_reason") == "declined_by_gate"
        for e in final.events
    )


@pytest.mark.asyncio
async def test_budget_exceeded_halts(monkeypatch):
    async def ok_step(room_id, ctx):
        # burn budget as a side-effect
        ctx.usage["tokens"] = ctx.budgets["tokens"] + 1
        return types.SimpleNamespace(status=StepStatus.OK, outputs={}, errors=[], metrics={})

    monkeypatch.setattr(orch_mod, "run_step", ok_step)

    # set a tiny token budget so the first step exceeds it
    c = _ctx("r3")
    c.budgets["tokens"] = 0.0

    final = await run_hallway(c)

    # orchestrator should emit a budget_exceeded event and stop early
    assert any(
        isinstance(e, dict) and e.get("reason") == "budget_exceeded"
        for e in final.events
    )
