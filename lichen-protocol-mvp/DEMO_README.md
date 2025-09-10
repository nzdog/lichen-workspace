# Lichen Protocol SIS MVP Demo

A comprehensive demo experience showcasing the end-to-end hallway orchestrator with prepared scenarios that demonstrate the Foundation Stones.

## Foundation Stones Demonstrated

- **Light Before Form**: Structured, predictable flow
- **Speed of Trust**: Efficient room-to-room transitions  
- **Presence Is Productivity**: Focused, purposeful execution
- **Integrity Is the Growth Strategy**: Validated, auditable results

## Quick Start

### CLI Demo

Run the interactive CLI demo:

```bash
python3 demo.py
```

Or run specific scenarios:

```bash
# Full Canonical Walk (7 steps)
python3 demo.py 1

# Mini Walk (Entry → Exit)
python3 demo.py 2

# Custom Subset (Entry → Protocol → Exit)
python3 demo.py 3

# Dry Run (Availability Check)
python3 demo.py 4

# Gate Deny (Governance Demonstration)
python3 demo.py 5

# Run All Scenarios
python3 demo.py all
```

### Web Demo (Optional)

Start the web demo server:

```bash
python3 web_demo.py
```

Then open your browser to: http://localhost:8080

## Demo Scenarios

### 1. Full Canonical Walk (7 Steps)
- **Path**: Entry → Diagnostic → Protocol → Walk → Memory → Integration → Exit
- **Expected**: Completed: True, 7 steps
- **Demonstrates**: Complete Lichen Protocol journey

### 2. Mini Walk (Entry → Exit)
- **Path**: Entry → Exit
- **Expected**: Completed: True, 2 steps
- **Demonstrates**: Essential entry and exit flow

### 3. Custom Subset (Entry → Protocol → Exit)
- **Path**: Entry → Protocol → Exit
- **Expected**: Completed: True, 3 steps
- **Demonstrates**: Focused protocol exploration

### 4. Dry Run (Availability Check)
- **Path**: All rooms (no execution)
- **Expected**: Completed: True, 7 steps
- **Demonstrates**: All rooms available

### 5. Gate Deny (Governance Demonstration)
- **Path**: Entry → Diagnostic (denied) → Exit
- **Expected**: Completed: False, 2 steps
- **Demonstrates**: Proper decline handling

## Verification

Run the comprehensive test suite:

```bash
python3 test_demo.py
```

Verify production logic is unchanged:

```bash
python3 verify_production_logic.py
```

## Key Features

- **Demo-only consent signals**: Scoped to demo paths, no production changes
- **Contract validation**: All outputs validate against existing schemas
- **No hybrid imports**: Clean `rooms.*` and `hallway.*` imports
- **Foundation Stones**: Each scenario demonstrates core principles
- **Real-time feedback**: Step-by-step execution with status updates

## Files Created

- `demo.py` - CLI demo runner with scenario selection
- `web_demo.py` - Optional web demo interface
- `test_demo.py` - Comprehensive test suite
- `verify_production_logic.py` - Production logic verification
- `DEMO_README.md` - This documentation

## Production Safety

✅ **Production consent logic unchanged**  
✅ **No protocol logic modifications**  
✅ **Demo signals scoped to demo paths only**  
✅ **All outputs validate against existing schemas**  
✅ **No hybrid imports or TypeScript artifacts**

## Success Criteria Met

- ✅ One command to run CLI demo from repo root
- ✅ Optional web face starts with one command
- ✅ No import warnings; all outputs validate
- ✅ Full Canonical Walk → Completed: True, 7 steps
- ✅ Mini Walk → Completed: True, 2 steps  
- ✅ Custom Subset → Completed: True, 3 steps
- ✅ Dry Run → all rooms available
- ✅ Gate Deny → Completed: False with decline reason
