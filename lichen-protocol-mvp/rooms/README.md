# Entry Room Implementation (Python)

A complete, production-ready Python 3.11 implementation of the Entry Room for the Lichen Protocol Room Architecture (PRA).

## Overview

The Entry Room serves as the safe threshold where walks begin, implementing the Entry Room Protocol to receive the founder's first words, reflect them faithfully, set initial pacing, and establish consent before deeper protocols begin.

## Features

- **Faithful Reflection**: Mirrors input exactly without interpretation
- **Gate Chain**: Orchestrates gates in strict order with failure handling
- **Pace Setting**: Configurable pacing with action mapping
- **Consent Enforcement**: Explicit consent required before proceeding
- **Diagnostics**: Configurable diagnostic capture (enabled by default)
- **Completion Markers**: Always ends with detectable completion markers
- **Contract Compliance**: Strict adherence to I/O specifications
- **Error Handling**: Graceful error containment, never throws unhandled exceptions
- **Policy Injection**: All behaviors customizable via policy interfaces

## Installation

```bash
cd rooms
pip install -r requirements.txt
```

## Quick Start

### Basic Usage

```python
import asyncio
from entry_room import run_entry_room, EntryRoomInput

async def main():
    input_data = EntryRoomInput(
        session_state_ref='session-123',
        payload='I have concerns about the project timeline and quality.'
    )
    
    result = await run_entry_room(input_data)
    print(f"Display Text: {result.display_text}")
    print(f"Next Action: {result.next_action}")

asyncio.run(main())
```

### Advanced Configuration

```python
from entry_room import EntryRoom, EntryRoomConfig, CustomCompletionPolicy

config = EntryRoomConfig(
    completion=CustomCompletionPolicy('[COMPLETE]'),
    diagnostics_default=False
)

room = EntryRoom(config)
result = await room.run_entry_room(input_data)
```

## Architecture

### Core Components

- **`EntryRoom`**: Main orchestrator implementing the protocol flow
- **`VerbatimReflection`**: Handles faithful reflection of input
- **`GateChain`**: Orchestrates the gate chain in order
- **`PacePolicy`**: Manages session pacing and readiness
- **`ConsentPolicy`**: Enforces explicit consent before proceeding
- **`DiagnosticsPolicy`**: Captures diagnostic information when enabled
- **`CompletionPolicy`**: Adds completion markers to output

### Protocol Flow

1. **Faithful Reflection** → Mirror input exactly, one idea per line
2. **Pre-Gate Chain** → Run gates in order: integrity_linter → plain_language_rewriter → stones_alignment_filter → coherence_gate
3. **Pace Setting** → Determine session pacing (NOW/HOLD/LATER/SOFT_HOLD)
4. **Consent Anchor** → Require explicit consent before proceeding
5. **Diagnostics** → Capture diagnostic information (when enabled)
6. **Completion Prompt** → Add completion marker to output

## Behavioral Invariants

### 1. Faithful Reflection
- Input is mirrored exactly without interpretation or distortion
- Multiple ideas are separated into clean lines, preserving order
- No paraphrase or summarization is performed
- Handles various payload types gracefully

### 2. Gate Chain Execution
- Gates run in strict order: integrity_linter → plain_language_rewriter → stones_alignment_filter → coherence_gate
- Pipeline halts on first failure
- Failed gates return structured decline with gate name and notes
- All gates must pass for successful completion

### 3. Pace and Action Mapping
- PaceState determines next_action: NOW → 'continue', HOLD → 'hold', LATER → 'later'
- SOFT_HOLD is treated as 'hold'
- Pace policies are injectable and configurable

### 4. Consent Enforcement
- Explicit consent is required before allowing downstream flow
- Non-consent results in short-circuit with appropriate action
- Consent requests are clear and invitational
- Multiple consent models supported

### 5. Diagnostics Control
- Captured by default when diagnostics_default === true
- Can be disabled via configuration
- Failures don't break main flow
- Captures tone, residue, and readiness signals

### 6. Completion Requirements
- display_text always ends with a completion marker
- Markers are detectable and configurable
- Multiple marker formats supported
- Utility functions for marker management

## Contract Compliance

The implementation strictly adheres to the Entry Room Contract:

```python
@dataclass
class EntryRoomOutput:
    display_text: str
    next_action: Literal["continue", "hold", "later"]
```

- **No additional properties** exposed in the public interface
- **Strict type compliance** with contract specification
- **I/O validation** through Python type hints
- **Contract shape preservation** in all outputs

## Error Handling

### Comprehensive Error Containment
- **Malformed input**: Returns typed error with guidance
- **Gate failures**: Returns decline object with gate name and notes
- **Exceptions**: All errors are contained and returned as typed results
- **Never throws**: Unhandled exceptions are impossible

### Graceful Degradation
- **Diagnostics failure**: Doesn't break main flow
- **Gate exceptions**: Handled gracefully with error messages
- **Policy failures**: Fallback to default behaviors
- **Input validation**: Handles edge cases without crashing

## Testing

### Run Tests

```bash
pytest rooms/entry_room/tests/test_entry_room.py
```

### Test Coverage

The test suite covers:
- **Faithful Reflection**: Multiline payloads, object handling, null cases
- **Gate Chain Order**: Sequential execution, failure handling, error messages
- **Pace Setting**: All pace states, action mapping, policy injection
- **Consent Anchor**: Enforcement, short-circuiting, different consent models
- **Diagnostics**: Capture, skipping, failure handling
- **Completion**: Marker addition, different formats, utility functions
- **Contract I/O**: Shape compliance, property validation
- **Error Handling**: Graceful degradation, exception containment
- **Integration**: Full flow scenarios, complex inputs

## Usage Examples

### Basic Usage

```python
from entry_room import run_entry_room, EntryRoomInput

input_data = EntryRoomInput(
    session_state_ref='session-123',
    payload='I have multiple concerns about the project timeline and quality.'
)

result = await run_entry_room(input_data)
print(result.display_text)    # Mirrored input + completion marker
print(result.next_action)     # 'continue' | 'hold' | 'later'
```

### Advanced Configuration

```python
from entry_room import EntryRoom, EntryRoomConfig, CustomCompletionPolicy

custom_completion = CustomCompletionPolicy('[COMPLETE]')
room = EntryRoom(EntryRoomConfig(
    completion=custom_completion,
    diagnostics_default=False
))

result = await room.run_entry_room(input_data)
```

### Custom Policies

```python
from entry_room import SimplePacePolicy, ExplicitConsentPolicy

room = EntryRoom(EntryRoomConfig(
    pace=SimplePacePolicy('HOLD'),
    consent=ExplicitConsentPolicy(True)
))
```

## Extensibility

### Policy Injection
- **Reflection policies**: Custom input processing
- **Gate configurations**: Custom gate implementations
- **Pace policies**: Custom pacing logic
- **Consent models**: Custom consent workflows
- **Diagnostic policies**: Custom diagnostic capture
- **Completion policies**: Custom marker formats

### Integration Points
- **Gate implementations**: Easy to integrate real gate services
- **External policies**: Can connect to external systems
- **Custom behaviors**: All aspects customizable
- **Plugin architecture**: Modular, extensible design

## Performance

- **Synchronous operations**: Reflection and completion are fast
- **Async gates**: Gate chain supports async operations
- **Caching**: Schemas and policies cached appropriately
- **Memory efficient**: Minimal allocations, no memory leaks

## Security

- **Input validation**: All input processed through the gate chain
- **Type safety**: Python type hints prevent invalid data structures
- **Consent enforcement**: Explicit consent prevents unauthorized progression
- **Error containment**: All errors contained within room boundary
- **No external calls**: No network or file system access by default

## Production Readiness

### Code Quality
- **Python 3.11**: Modern language features and type hints
- **Comprehensive testing**: Full test coverage of core paths
- **Error handling**: Robust error containment
- **Documentation**: Complete API documentation

### Deployment
- **No external dependencies**: Self-contained implementation
- **Configurable**: All behaviors customizable
- **Scalable**: Policy-based architecture supports growth
- **Maintainable**: Clean, modular code structure

## File Structure

```
rooms/
├── requirements.txt              # Python dependencies
├── README.md                    # This file
├── example_usage.py             # Usage examples
├── index.py                     # Main module exports
└── entry_room/
    ├── __init__.py              # Package initialization
    ├── types.py                 # Type definitions and interfaces
    ├── entry_room.py            # Main EntryRoom class and run_entry_room function
    ├── reflection.py            # Faithful reflection implementation
    ├── gates.py                 # Gate chain orchestration
    ├── pace.py                  # Pace setting policies
    ├── consent.py               # Consent enforcement
    ├── diagnostics.py           # Diagnostic capture
    ├── completion.py            # Completion markers
    └── tests/
        └── test_entry_room.py   # Comprehensive test suite
```

## License

This implementation follows the same licensing as the parent Lichen Protocol project.
