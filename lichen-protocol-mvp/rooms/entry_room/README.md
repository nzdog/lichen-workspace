# Entry Room Implementation

## Overview

The Entry Room is the first room in the Lichen Protocol Room Architecture (PRA). It serves as the safe threshold where walks begin, implementing the Entry Room Protocol to receive the founder's first words, reflect them faithfully, set initial pacing, and establish consent before deeper protocols begin.

## Architecture

The Entry Room follows a modular, policy-based architecture with the following components:

### Core Components

- **`EntryRoom`** - Main orchestrator class that implements the protocol flow
- **`VerbatimReflection`** - Handles faithful reflection of input without interpretation
- **`GateChain`** - Orchestrates the gate chain in the specified order
- **`PacePolicy`** - Manages session pacing and readiness
- **`ConsentPolicy`** - Enforces explicit consent before proceeding
- **`DiagnosticsPolicy`** - Captures diagnostic information when enabled
- **`CompletionPolicy`** - Adds completion markers to output

### Protocol Flow

1. **Faithful Reflection** → Mirror input exactly, one idea per line
2. **Pre-Gate Chain** → Run gates in order: integrity_linter → plain_language_rewriter → stones_alignment_filter → coherence_gate
3. **Pace Setting** → Determine session pacing (NOW/HOLD/LATER/SOFT_HOLD)
4. **Consent Anchor** → Require explicit consent before proceeding
5. **Diagnostics** → Capture diagnostic information (when enabled)
6. **Completion Prompt** → Add completion marker to output

## Usage

### Basic Usage

```typescript
import { runEntryRoom, EntryRoomInput } from './rooms/entry_room';

const input: EntryRoomInput = {
  session_state_ref: 'session-123',
  payload: 'I have multiple concerns about the project timeline and quality.'
};

const output = await runEntryRoom(input);
console.log(output.display_text);
console.log(output.next_action); // 'continue' | 'hold' | 'later'
```

### Advanced Configuration

```typescript
import { EntryRoom, CustomCompletionPolicy } from './rooms/entry_room';

const customCompletion = new CustomCompletionPolicy('[COMPLETE]');
const room = new EntryRoom({
  completion: customCompletion,
  diagnostics_default: false
});

const output = await room.runEntryRoom(input);
```

### Custom Policies

```typescript
import { SimplePacePolicy, ExplicitConsentPolicy } from './rooms/entry_room';

const room = new EntryRoom({
  pace: new SimplePacePolicy('HOLD'),
  consent: new ExplicitConsentPolicy(true)
});
```

## Behavioral Invariants

### Faithful Reflection
- Input is mirrored exactly without interpretation or distortion
- Multiple ideas are separated into clean lines, preserving order
- No paraphrase or summarization is performed

### Gate Chain
- Gates run in strict order: integrity_linter → plain_language_rewriter → stones_alignment_filter → coherence_gate
- Pipeline halts on first gate failure
- Failed gates return structured decline with gate name and notes

### Pace Setting
- PaceState determines next_action: NOW → 'continue', HOLD → 'hold', LATER → 'later'
- SOFT_HOLD is treated as 'hold'

### Consent Anchor
- Explicit consent is required before allowing downstream flow
- Non-consent results in short-circuit with appropriate action
- Consent requests are clear and invitational

### Diagnostics
- Captured by default when diagnostics_default === true
- Can be disabled via configuration
- Failures don't break main flow

### Completion
- display_text always ends with a completion marker
- Markers are detectable and configurable

## Contract Compliance

The implementation strictly adheres to the Entry Room Contract:

```typescript
interface EntryRoomOutput {
  display_text: string;
  next_action: 'continue' | 'hold' | 'later';
}
```

No additional properties are exposed in the public interface.

## Error Handling

- **Malformed Input**: Returns typed error with guidance
- **Gate Failures**: Returns decline object with gate name and notes
- **Exceptions**: All errors are contained and returned as typed results
- **Never Throws**: Unhandled exceptions are impossible

## Testing

Run the comprehensive test suite:

```bash
cd rooms
npm test
```

Tests cover all behavioral invariants, edge cases, and integration scenarios.

## Dependencies

- **Framework**: TypeScript-first, Node.js compatible
- **External Dependencies**: None (all dependencies are injectable)
- **Testing**: Jest with TypeScript support

## Extensibility

The Entry Room is designed for extensibility:

- **Policy Injection**: All behaviors can be customized via policy interfaces
- **Gate Integration**: Easy to integrate with real gate implementations
- **Diagnostics**: Configurable diagnostic capture and analysis
- **Pacing**: Customizable pace determination logic
- **Consent**: Flexible consent models and workflows

## Performance

- **Synchronous Operations**: Reflection and completion are synchronous
- **Async Gates**: Gate chain supports async operations
- **Caching**: Schemas and policies are cached appropriately
- **Memory**: Minimal memory footprint with no unnecessary allocations

## Security

- **Input Validation**: All input is validated through the gate chain
- **Consent Enforcement**: Explicit consent prevents unauthorized progression
- **Error Containment**: All errors are contained within the room boundary
- **No External Calls**: No network or file system access by default
