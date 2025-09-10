# Walk Room

## Overview

The Walk Room is a core component of the Lichen Protocol Room Architecture (PRA) that executes canon protocols step by step, enforcing sequence, pacing, diagnostics, and closure. It ensures protocols are enacted as structured processes rather than delivered as static content.

## Core Purpose

The Walk Room guarantees sequential delivery, pacing governance, diagnostic capture, and completion enforcement. Without it, protocols would be delivered all at once, skipped, or rushed, breaking structural fidelity and preventing downstream rooms from relying on consistent state.

## Key Features

### 1. Sequence Enforcement ✅
- **Canonical Order**: Delivers protocol themes in canonical order, one at a time
- **No Skipping**: Prevents skipping or collapsing steps, protecting structural fidelity
- **State Machine**: PENDING → IN_STEP → COMPLETED progression

### 2. Pacing Governance ✅
- **Pace States**: NOW, HOLD, LATER, SOFT_HOLD for each step
- **Action Mapping**: Deterministic mapping to next_action (continue/hold/later)
- **Structural Respect**: HOLD/LATER prevent advancement until conditions are met

### 3. Step Diagnostics ✅
- **Capture-Only**: Minimal structured diagnostics at each step
- **No Interpretation**: No sentiment analysis, NLP, or heuristics
- **Structured Data**: step_index, tone_label, residue_label, readiness_state

### 4. Completion Enforcement ✅
- **Closure Required**: Final completion prompt enforced before termination
- **State Protection**: Blocks termination until closure confirmed
- **Fixed Marker**: Appends exactly one `[[COMPLETE]]` marker

## Architecture

### File Structure
```
rooms/walk_room/
├── __init__.py              # Package initialization
├── walk_room.py             # Main orchestrator
├── sequencer.py             # Sequence enforcement
├── pacing.py                # Pace governance
├── step_diag.py             # Step diagnostics
├── completion.py            # Completion enforcement
├── contract_types.py        # Data structures
├── README.md                # This file
└── tests/
    └── test_walk_room.py    # Comprehensive test suite
```

### Core Components

#### WalkRoom Class
- **Main Orchestrator**: Coordinates the full walk flow
- **Session Management**: Maintains walk sessions and protocol structures
- **Action Routing**: Routes inputs to appropriate handlers
- **Error Handling**: Graceful degradation with structured responses

#### StepSequencer
- **Sequence Control**: Manages step progression and prevents violations
- **State Validation**: Ensures sequence integrity and canonical order
- **Navigation**: Supports advance, retreat, and jump operations

#### PaceGovernor
- **Pace Validation**: Validates pace states and maps to actions
- **Deterministic Logic**: Rule-based pacing without heuristics
- **Guidance**: Provides human-readable pace descriptions and guidance

#### StepDiagnosticCapture
- **Capture-Only**: Records diagnostics without interpretation
- **Structured Format**: Consistent diagnostic data structure
- **Validation**: Ensures diagnostic data integrity

#### WalkCompletion
- **Closure Enforcement**: Requires completion confirmation
- **Summary Generation**: Creates comprehensive walk summaries
- **Marker Appending**: Appends fixed completion marker

## Usage

### Starting a Walk

```python
from rooms.walk_room import run_walk_room
from rooms.walk_room.contract_types import WalkRoomInput

# Start a new protocol walk
input_data = WalkRoomInput(
    session_state_ref='session-123',
    payload={
        'protocol_id': 'grounding_protocol',
        'title': 'Grounding Protocol',
        'steps': [
            {
                'title': 'Grounding Breath',
                'content': 'Take 3 deep breaths',
                'description': 'Begin with grounding breath practice',
                'estimated_time': 2
            },
            {
                'title': 'Resource Inventory',
                'content': 'List 3 personal resources',
                'description': 'Identify your current resources',
                'estimated_time': 3
            }
        ]
    }
)

result = run_walk_room(input_data)
# Returns first step with pacing requirement
```

### Setting Pace for a Step

```python
# Set pace for current step
pace_input = WalkRoomInput(
    session_state_ref='session-123',
    payload={'pace': 'NOW'}
)

result = run_walk_room(pace_input)
# Returns step with pace information and next_action
```

### Advancing to Next Step

```python
# Advance to next step (requires pace to be set)
advance_input = WalkRoomInput(
    session_state_ref='session-123',
    payload={'action': 'advance_step'}
)

result = run_walk_room(advance_input)
# Returns next step
```

### Getting Walk Status

```python
# Get current walk status
status_input = WalkRoomInput(
    session_state_ref='session-123',
    payload={'action': 'get_walk_status'}
)

result = run_walk_room(status_input)
# Returns walk status and progress
```

### Confirming Completion

```python
# Confirm walk completion
complete_input = WalkRoomInput(
    session_state_ref='session-123',
    payload={'action': 'confirm_completion'}
)

result = run_walk_room(complete_input)
# Returns completion summary with [[COMPLETE]] marker
```

## Design Principles

### 1. Deterministic Behavior
- **No AI or Heuristics**: All logic is rule-based and predictable
- **Static Rules**: Pacing and sequence rules are fixed
- **Explicit Control**: Actions controlled by explicit input flags

### 2. Sequence Integrity
- **Canonical Order**: Steps delivered in exact order
- **No Skipping**: All steps must be processed
- **State Consistency**: Walk state always consistent

### 3. Pacing Governance
- **Every Step**: Pace required for each step
- **Structural Respect**: HOLD/LATER create structural pauses
- **Deterministic Mapping**: Clear pace → action relationships

### 4. Capture-Only Diagnostics
- **No Interpretation**: Raw data capture only
- **Minimal Structure**: Essential fields without complexity
- **Toggle Support**: Diagnostics can be disabled without breaking flow

### 5. Completion Enforcement
- **Closure Required**: Explicit completion confirmation
- **State Protection**: Prevents incomplete termination
- **Fixed Marker**: Single completion marker, no variants

## Contract Compliance

### Input Contract
```python
@dataclass
class WalkRoomInput:
    session_state_ref: str
    payload: Any
```

### Output Contract
```python
@dataclass
class WalkRoomOutput:
    display_text: str
    next_action: Literal["continue"]
```

### Supported Actions
- `start_walk`: Initialize new protocol walk
- `get_current_step`: Get current step (default)
- `advance_step`: Move to next step
- `set_pace`: Set pace for current step
- `confirm_completion`: Confirm walk completion
- `get_walk_status`: Get walk status and progress

## Testing

### Test Coverage
The Walk Room includes comprehensive test coverage:

- **Sequence Enforcement**: Step delivery and navigation
- **Pacing Governance**: Pace validation and action mapping
- **Step Diagnostics**: Capture and validation
- **Completion**: Closure enforcement and marker appending
- **Contract I/O**: Schema compliance verification
- **Error Handling**: Graceful degradation testing
- **Integration**: End-to-end walk flow testing

### Running Tests
```bash
pytest rooms/walk_room/tests/test_walk_room.py
```

## Error Handling

### Structured Declines
All errors return structured decline responses:
- **Error Message**: Clear description of what went wrong
- **State Preservation**: No state mutation on errors
- **Graceful Degradation**: System continues to function

### Common Error Scenarios
- **Invalid Session**: No active walk session
- **Invalid Pace**: Unsupported pace state
- **Sequence Violation**: Attempted invalid navigation
- **Missing Data**: Required payload fields missing

## Production Readiness

### Code Quality
- **Python 3.11+**: Modern language features and type hints
- **Clean Architecture**: Modular design with clear separation
- **Comprehensive Testing**: Full test coverage and validation
- **Error Handling**: Robust error handling and recovery

### Performance
- **Session Management**: Efficient session storage and retrieval
- **Deterministic Logic**: Predictable performance characteristics
- **Minimal Overhead**: Lightweight implementation

### Maintainability
- **Clear Structure**: Logical file organization
- **Type Safety**: Full type hints for better IDE support
- **Documentation**: Comprehensive API documentation
- **Test Coverage**: Regression prevention through testing

## Integration

### Upstream Dependencies
- **Protocol Room**: Receives protocol structures and steps
- **Session Management**: Requires session state references

### Downstream Consumers
- **Diagnostic Systems**: Receives step-level diagnostic data
- **State Management**: Provides consistent walk state
- **Completion Handlers**: Receives completion signals

## Future Enhancements

### Potential Improvements
- **Persistence**: Session state persistence across restarts
- **Analytics**: Walk completion and pacing analytics
- **Customization**: Configurable pacing and diagnostic options
- **Integration**: Enhanced integration with other PRA rooms

### Extension Points
- **Custom Pacing**: Additional pace state types
- **Enhanced Diagnostics**: Extended diagnostic fields
- **Workflow Integration**: Integration with external workflow systems

## Conclusion

The Walk Room provides a robust, deterministic foundation for protocol execution within the Lichen Protocol Room Architecture. It ensures structural fidelity, enforces pacing governance, captures essential diagnostics, and guarantees proper completion.

By maintaining strict adherence to design principles and contract compliance, the Walk Room enables reliable, predictable protocol execution that downstream systems can depend on for consistent state and behavior.
