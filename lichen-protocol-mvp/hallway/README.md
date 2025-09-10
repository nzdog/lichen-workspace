# Hallway Protocol Implementation

A deterministic multi-room session orchestrator that implements the Hallway Protocol v0.2. The Hallway provides a single source of truth for room sequencing, gate enforcement, error containment, and audit trails.

## Overview

The Hallway Protocol ensures:
- **Deterministic Sequencing**: Run the declared room sequence exactly once each
- **Gate Enforcement**: Evaluate gate chains before each room and short-circuit on deny
- **State Continuity & Atomicity**: Carry forward session state atomically with no partial commits
- **Error Containment**: Fail fast with structured declines; never crash the process
- **Observability & Audit**: Emit structured events and produce auditable hallway summaries

## Architecture

```
hallway/
├── __init__.py              # Module exports
├── hallway.py               # HallwayOrchestrator (main orchestrator)
├── upcaster.py              # v0.1 → v0.2 StepResult envelope transformer
├── gates.py                 # Gate interface and coherence gate implementation
├── audit.py                 # Canonical JSON and SHA256 hashing utilities
├── schemas/                 # v0.2 JSON Schema for runtime validation
│   └── hallway_v0_2.schema.json
├── config/                  # Hallway configuration
│   └── hallway.contract.json
├── example_usage.py         # Usage examples
└── tests/                   # Test suite
    ├── test_hallway_happy.py
    ├── test_hallway_decline.py
    ├── test_upcaster_roundtrip.py
    └── test_schema_validation.py
```

## Key Components

### HallwayOrchestrator

The main orchestrator class that:
- Runs the canonical sequence of rooms deterministically
- Enforces gate chains before each room
- Wraps each room's v0.1 output in a v0.2 StepResult envelope
- Returns an object that validates against the Hallway v0.2 JSON Schema

### Upcaster

Transforms each room's v0.1 output into a v0.2 StepResult envelope:
- Places legacy room output under `data` field
- Adds invariants (deterministic, no_partial_write)
- Adds gate decisions
- Computes audit hashes
- Maintains backward compatibility

### Gates

Gate enforcement system:
- **GateInterface**: Base interface for all gates
- **CoherenceGate**: Default gate that checks basic coherence requirements
- **evaluate_gate_chain**: Function to evaluate a chain of gates

### Audit

Utilities for canonical JSON and hashing:
- **canonical_json**: Stable JSON serialization for deterministic hashing
- **sha256_hex**: SHA256 hash computation
- **compute_step_hash**: Step hash computation over room outputs
- **build_audit_chain**: Linear chain of step hashes for verification

## Usage

### Basic Usage

```python
from hallway import HallwayOrchestrator, run_hallway

# Load contract configuration
with open("hallway/config/hallway.contract.json", "r") as f:
    contract = json.load(f)

# Create orchestrator
orchestrator = HallwayOrchestrator(contract)

# Run full sequence
result = await orchestrator.run(
    session_state_ref="session-123",
    payloads={
        "entry_room": {"user_input": "Hello"},
        "protocol_room": {"protocol_type": "standard"}
    }
)
```

### Convenience Function

```python
# Use the convenience function with default contract
result = await run_hallway(
    session_state_ref="session-456",
    options={"mini_walk": True}  # Run first three rooms (or fewer)
)
```

### Custom Gate Configuration

```python
from hallway.gates import GateInterface, GateDecision

class CustomGate(GateInterface):
    def evaluate(self, room_id: str, session_state_ref: str, payload: dict = None) -> GateDecision:
        # Custom gate logic
        if room_id == "sensitive_room":
            return GateDecision(
                gate="custom_gate",
                allow=False,
                reason="Sensitive room access denied"
            )
        return GateDecision(
            gate="custom_gate",
            allow=True,
            reason="Access granted"
        )

# Use custom gate
gates = {"coherence_gate": CustomGate()}
orchestrator = HallwayOrchestrator(contract, gates)
```

## Configuration

The hallway configuration is defined in `config/hallway.contract.json`:

```json
{
  "room_id": "hallway",
  "title": "Hallway",
  "version": "0.2.0",
  "purpose": "Deterministic multi-room session orchestrator",
  "stone_alignment": ["deterministic", "atomic", "auditable"],
  "sequence": [
    "entry_room",
    "diagnostic_room",
    "protocol_room",
    "walk_room",
    "memory_room",
    "integration_commit_room",
    "exit_room"
  ],
  "mini_walk_supported": true,
  "gate_profile": {
    "chain": ["coherence_gate"],
    "overrides": {}
  }
}
```

## Options

The `run()` method accepts various options:

- **stop_on_decline**: Stop execution on first gate/room decline (default: true)
- **dry_run**: Execute without running actual rooms (default: false)
- **mini_walk**: Run first three rooms (default: false)
- **rooms_subset**: Custom subset of rooms to execute (default: [])

## Output Structure

The hallway returns a v0.2 contract-compliant output:

```json
{
  "room_id": "hallway",
  "version": "0.2.0",
  "outputs": {
    "contract_version": "0.2.0",
    "steps": [
      {
        "contract_version": "0.2.0",
        "room_id": "entry_room",
        "status": "ok",
        "data": { /* v0.1 room output */ },
        "invariants": {"deterministic": true, "no_partial_write": true},
        "gate_decisions": [{"gate": "coherence_gate", "allow": true}],
        "audit": {
          "step_hash": "sha256:...",
          "prev_hash": null,
          "room_contract_version": "0.1.0"
        }
      }
    ],
    "exit_summary": {
      "completed": true,
      "decline": null,
      "auditable_hash_chain": ["sha256:..."]
    }
  }
}
```

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest hallway/tests/

# Run specific test file
python -m pytest hallway/tests/test_hallway_happy.py

# Run with coverage
python -m pytest hallway/tests/ --cov=hallway
```

## Examples

See `example_usage.py` for comprehensive examples of:
- Full canonical sequence execution
- Mini-walk execution
- Custom room subsets
- Dry run execution
- Gate deny behavior

## Dependencies

- Python 3.7+
- jsonschema (for runtime validation)
- pytest (for testing)
- pytest-asyncio (for async test support)

## Design Principles

- **Deterministic**: No heuristics or AI - predictable behavior
- **Atomic**: No partial writes inside Hallway
- **Backward Compatible**: Rooms remain at v0.1, transcendent fields in Hallway envelope
- **Auditable**: Full audit chain for external verification
- **Resumable**: Structured declines enable resumption from last safe state
