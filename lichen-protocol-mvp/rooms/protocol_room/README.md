# Protocol Room

A Python 3.11 implementation of the Protocol Room for the Lichen Protocol Room Architecture (PRA). The Protocol Room serves as the bridge between diagnostic sensing and the living canon, surfacing the most fitting protocols with integrity and coherence.

## Overview

The Protocol Room is responsible for:
- **Canon Fidelity**: Delivering protocol text exactly as authored without distortion
- **Depth Selection**: Offering protocols at the right depth (full, theme, scenario)
- **Scenario Mapping**: Linking founder scenarios to relevant protocols
- **Integrity Gate**: Running protocols through Stones alignment and coherence checks
- **Completion**: Ensuring all output includes the completion marker

## Design Stance

This implementation follows strict design principles:
- **No AI or heuristics**: All logic is deterministic and rule-based
- **Exact text delivery**: Protocol text is never edited or paraphrased
- **Static registries**: Scenario mapping uses predefined relationships
- **Integrity enforcement**: All protocols must pass Stones and coherence checks
- **Single completion marker**: Always `[[COMPLETE]]`, no variants

## Architecture

The Protocol Room is built with a modular architecture:

```
protocol_room/
├── __init__.py              # Package initialization
├── types.py                 # Type definitions and data structures
├── protocol_room.py         # Main orchestrator class
├── canon.py                 # Canon fidelity and text retrieval
├── depth.py                 # Depth selection logic
├── mapping.py               # Scenario to protocol mapping
├── integrity.py             # Integrity gate implementation
├── completion.py            # Completion marker logic
├── example_usage.py         # Usage examples
├── README.md                # This documentation
└── tests/
    └── test_protocol_room.py # Comprehensive test suite
```

## Core Components

### 1. ProtocolRoom Class
Main orchestrator that coordinates the entire protocol flow:
- Determines protocol ID from input or scenario mapping
- Selects appropriate depth based on readiness and time
- Fetches exact text from canon
- Runs integrity gate checks
- Formats output with completion marker

### 2. Canon Module
Manages protocol text storage and retrieval:
- Static canon store with sample protocols
- Exact text delivery without modification
- Support for full, theme, and scenario depths
- No editing, paraphrasing, or distortion

### 3. Depth Module
Handles protocol depth selection:
- Deterministic logic based on readiness level
- Time-based depth selection
- Explicit depth override support
- Consistent depth labeling and description

### 4. Mapping Module
Provides scenario to protocol mapping:
- Static registry of scenario relationships
- Deterministic mapping logic
- Support for common scenario variations
- Default protocol fallback

### 5. Integrity Module
Implements the integrity gate:
- Stones alignment checking
- Coherence validation
- Structured integrity results
- Graceful failure handling

### 6. Completion Module
Ensures completion marker requirements:
- Fixed `[[COMPLETE]]` marker
- Single marker enforcement
- No variants or policies

## Usage

### Basic Protocol Request

```python
from protocol_room import run_protocol_room, ProtocolRoomInput

input_data = ProtocolRoomInput(
    session_state_ref='session-123',
    payload={
        'protocol_id': 'clearing_entry',
        'depth': 'theme'
    }
)

result = run_protocol_room(input_data)
print(result.display_text)    # Protocol text + [[COMPLETE]]
print(result.next_action)     # Always "continue"
```

### Scenario-Based Selection

```python
input_data = ProtocolRoomInput(
    session_state_ref='session-456',
    payload={
        'scenario': 'overwhelm',
        'depth': 'scenario'
    }
)

result = run_protocol_room(input_data)
# Automatically maps 'overwhelm' to 'resourcing_mini_walk'
```

### Readiness-Based Depth

```python
input_data = ProtocolRoomInput(
    session_state_ref='session-789',
    payload={
        'protocol_id': 'integration_pause',
        'readiness_level': 'HOLD'  # Will select 'scenario' depth
    }
)
```

### Time-Based Depth

```python
input_data = ProtocolRoomInput(
    session_state_ref='session-101',
    payload={
        'protocol_id': 'resourcing_mini_walk',
        'time_available': 5  # Will select 'scenario' depth
    }
)
```

## Protocol Registry

The Protocol Room includes a sample canon with these protocols:

- **`resourcing_mini_walk`**: Quick grounding and resource reconnection
- **`clearing_entry`**: Mental decluttering and emotional clearing
- **`pacing_adjustment`**: Pace assessment and adjustment
- **`integration_pause`**: Insight integration and reflection

## Scenario Mapping

Common scenarios are mapped to protocols:

- **`overwhelm`** → `resourcing_mini_walk`
- **`urgency`** → `clearing_entry`
- **`boundary_violation`** → `boundary_setting`
- **`communication_breakdown`** → `deep_listening`
- **`decision_fatigue`** → `integration_pause`
- **`team_conflict`** → `deep_listening`
- **`personal_crisis`** → `resourcing_mini_walk`
- **`growth_edge`** → `pacing_adjustment`

## Integrity Gate

All protocols must pass integrity checks:

1. **Stones Alignment**: Checks for integrity, clarity, and care indicators
2. **Coherence**: Validates structure, length, and clarity
3. **Failure Handling**: Returns structured decline with specific reasons

## Contract Compliance

The Protocol Room strictly adheres to its contract:

- **Input**: `ProtocolRoomInput` with `session_state_ref` and `payload`
- **Output**: `ProtocolRoomOutput` with `display_text` and `next_action`
- **Behavior**: Always returns "continue" as next_action
- **Completion**: All output includes `[[COMPLETE]]` marker

## Testing

Run the comprehensive test suite:

```bash
pytest rooms/protocol_room/tests/test_protocol_room.py
```

Tests cover:
- Canon fidelity and exact text delivery
- Depth selection logic
- Scenario mapping accuracy
- Integrity gate functionality
- Completion marker requirements
- Contract I/O compliance
- Error handling and edge cases
- No TypeScript artifacts

## Error Handling

The Protocol Room handles errors gracefully:
- Missing protocols return error messages
- Integrity gate failures produce decline responses
- All errors include completion markers
- No unhandled exceptions are thrown

## Production Readiness

This implementation is production-ready with:
- **Type Safety**: Full Python type hints
- **Error Handling**: Graceful degradation for all failure modes
- **Testing**: Comprehensive test coverage
- **Documentation**: Clear usage examples and API reference
- **Modularity**: Clean separation of concerns
- **Extensibility**: Easy to add new protocols and scenarios

## Extending the Canon

To add new protocols:

1. Add protocol definition to `CANON_STORE` in `canon.py`
2. Include `full_text`, `theme_text`, and `scenario_text`
3. Add protocol ID to `Protocols` class in `types.py`
4. Update scenario mappings in `mapping.py` if needed
5. Add tests for new functionality

## License

This implementation follows the same licensing as the parent Lichen Protocol project.
