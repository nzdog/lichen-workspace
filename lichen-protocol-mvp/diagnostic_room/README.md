# Diagnostic Room Implementation (Python)

A complete, production-ready Python 3.11 implementation of the Diagnostic Room for the Lichen Protocol Room Architecture (PRA).

## Overview

The Diagnostic Room serves as the system's listening chamber—where the field is read before deciding the path forward. It senses tones, residues, and readiness at the start or during a walk, and maps these signals to the most fitting next protocols.

## Features

- **Capture-Only Sensing**: Records minimal signals without interpretation
- **Deterministic Readiness Assessment**: Rule-based readiness tagging
- **Protocol Mapping**: Maps signals to suggested protocols with rationale
- **Silent Capture**: Records diagnostic data for continuity across sessions
- **Single Completion Marker**: Always ends with `[[COMPLETE]]`
- **Contract Compliance**: Strict adherence to I/O specifications
- **No Consent Logic**: Consent handled upstream
- **Deterministic Functions**: No policies, no variants, no heuristics

## Design Stance

### Strict Implementation
- **Capture-only diagnostics**: No interpretation, no sentiment analysis, no ML
- **No consent logic**: Diagnostic Room does not solicit or enforce consent
- **Single completion marker**: Exactly `[[COMPLETE]]` appended once
- **No policy variants**: Deterministic functions only
- **Contract compliance**: Honor schema verbatim for inputs/outputs

## Architecture

### Core Components

- **`DiagnosticRoom`**: Main orchestrator implementing the protocol flow
- **`capture_tone_and_residue`**: Capture-only sensing without interpretation
- **`assess_readiness`**: Deterministic readiness assessment
- **`map_to_protocol`**: Rule-based protocol mapping
- **`capture_diagnostics`**: Minimal memory write with toggle respect
- **`append_fixed_marker`**: Single completion marker addition

### Protocol Flow

1. **Sensing** → Capture tone_label and residue_label from input
2. **Readiness Assessment** → Compute readiness tag (NOW/HOLD/LATER/SOFT_HOLD)
3. **Protocol Mapping** → Map signals to suggested protocol with rationale
4. **Silent Capture** → Record minimal structured data if enabled
5. **Completion** → Add `[[COMPLETE]]` marker to display_text

## Usage

### Basic Usage

```python
from diagnostic_room import run_diagnostic_room, DiagnosticRoomInput

input_data = DiagnosticRoomInput(
    session_state_ref='session-123',
    payload='I feel overwhelmed and still have unresolved issues.'
)

result = run_diagnostic_room(input_data)
print(result.display_text)    # Diagnostic info + [[COMPLETE]]
print(result.next_action)     # Always "continue"
```

### Explicit Signals

```python
input_data = DiagnosticRoomInput(
    session_state_ref='session-456',
    payload={
        'tone_label': 'urgency',
        'residue_label': 'previous_attempts',
        'readiness_state': 'NOW'
    }
)

result = run_diagnostic_room(input_data)
```

### Diagnostics Toggle

```python
# Disable diagnostics capture
result = run_diagnostic_room(input_data, diagnostics_enabled=False)
```

## Contract Compliance

The implementation strictly adheres to the Diagnostic Room Contract:

```python
@dataclass
class DiagnosticRoomOutput:
    display_text: str
    next_action: Literal["continue"]
```

- **No additional properties** exposed in the public interface
- **Strict type compliance** with contract specification
- **I/O validation** through Python type hints
- **Contract shape preservation** in all outputs

## Diagnostic Data Structure

When diagnostics are enabled, minimal structured data is captured:

```python
{
    "tone_label": str,
    "residue_label": str,
    "readiness_state": str,
    "suggested_protocol_id": str
}
```

## Protocol Registry

Static protocol registry for deterministic mapping:

- **`resourcing_mini_walk`**: For overwhelm tone
- **`clearing_entry`**: For urgency tone, default protocol
- **`pacing_adjustment`**: For worry tone, deferring residue
- **`integration_pause`**: For unresolved previous residue, HOLD readiness

## Testing

### Run Tests

```bash
pytest rooms/diagnostic_room/tests/test_diagnostic_room.py
```

### Test Coverage

The test suite covers:
- **Capture-only sensing**: No interpretation, defaults to "unspecified"
- **Readiness tagging**: All four states, deterministic mapping
- **Mapping registry**: Deterministic selection, fixed template rationale
- **Diagnostics toggle**: Enabled vs disabled, never blocks flow
- **Completion marker**: Single `[[COMPLETE]]`, no variants
- **Contract I/O**: Schema compliance, field types
- **No TS artifacts**: Ensures clean Python implementation

## File Structure

```
diagnostic_room/
├── __init__.py              # Package initialization
├── types.py                 # Type definitions and protocol registry
├── diagnostic_room.py       # Main DiagnosticRoom class and run_diagnostic_room function
├── sensing.py               # Capture-only tone and residue sensing
├── readiness.py             # Deterministic readiness assessment
├── mapping.py               # Rule-based protocol mapping
├── capture.py               # Minimal diagnostic capture and memory write
├── completion.py            # Fixed completion marker
├── example_usage.py         # Usage examples
├── README.md                # This file
└── tests/
    └── test_diagnostic_room.py  # Comprehensive test suite
```

## Behavioral Invariants

### 1. Capture-Only Sensing
- Extracts tone_label and residue_label without interpretation
- Defaults to "unspecified" if signals not explicitly provided
- No NLP, no sentiment analysis, no heuristics

### 2. Deterministic Readiness
- Computes readiness tag using rule-based logic only
- Supports all four states: NOW, HOLD, LATER, SOFT_HOLD
- No learning, no heuristics, no ML

### 3. Protocol Mapping
- Rule-based selection from static registry
- Fixed template rationale format
- Deterministic mapping based on signals

### 4. Silent Capture
- Minimal structured data when enabled
- Clean skip when disabled
- Never blocks main flow

### 5. Completion Requirement
- display_text always ends with `[[COMPLETE]]`
- Single marker only, no variants
- Fixed string, no policies

## Error Handling

### Graceful Degradation
- **Input errors**: Handled gracefully with error messages
- **Processing failures**: Fallback to safe defaults
- **Never throws**: Unhandled exceptions are impossible

### Error Output
- Error messages included in display_text
- Completion marker still appended
- next_action remains "continue"

## Performance

- **Fast execution**: Deterministic functions with no external calls
- **Memory efficient**: Minimal data structures
- **No blocking**: Diagnostics toggle never blocks flow
- **Stateless**: Pure functions for easy testing

## Security

- **No external calls**: Self-contained implementation
- **Input validation**: Type-safe through Python hints
- **No consent logic**: Handled upstream
- **Deterministic**: Predictable behavior

## Production Readiness

### Code Quality
- **Python 3.11**: Modern language features and type hints
- **Comprehensive testing**: Full test coverage of core paths
- **Error handling**: Robust error containment
- **Documentation**: Complete API documentation

### Deployment
- **No external dependencies**: Self-contained implementation
- **Configurable**: Diagnostics toggle for different environments
- **Scalable**: Static registry easy to extend
- **Maintainable**: Clean, modular code structure

## License

This implementation follows the same licensing as the parent Lichen Protocol project.
