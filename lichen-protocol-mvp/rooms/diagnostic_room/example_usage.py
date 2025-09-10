#!/usr/bin/env python3
"""
Example Usage of Diagnostic Room
Demonstrates basic and advanced usage patterns
"""

from rooms.diagnostic_room.diagnostic_room import run_diagnostic_room
from rooms.diagnostic_room.room_types import DiagnosticRoomInput


def basic_usage_example():
    """Basic usage example"""
    print("=== Basic Usage Example ===")
    
    # Create input
    input_data = DiagnosticRoomInput(
        session_state_ref='example-session-123',
        payload='I feel overwhelmed and still have unresolved issues from yesterday.'
    )
    
    # Run diagnostic room
    result = run_diagnostic_room(input_data)
    
    print(f"Display Text:\n{result.display_text}")
    print(f"Next Action: {result.next_action}")
    print()


def explicit_signals_example():
    """Example with explicit diagnostic signals"""
    print("=== Explicit Signals Example ===")
    
    # Create input with explicit signals
    input_data = DiagnosticRoomInput(
        session_state_ref='explicit-session-456',
        payload={
            'tone_label': 'urgency',
            'residue_label': 'previous_attempts',
            'readiness_state': 'NOW'
        }
    )
    
    # Run diagnostic room
    result = run_diagnostic_room(input_data)
    
    print(f"Display Text:\n{result.display_text}")
    print(f"Next Action: {result.next_action}")
    print()


def diagnostics_disabled_example():
    """Example with diagnostics disabled"""
    print("=== Diagnostics Disabled Example ===")
    
    # Create input
    input_data = DiagnosticRoomInput(
        session_state_ref='disabled-session-789',
        payload='I feel calm and ready to proceed'
    )
    
    # Run diagnostic room with diagnostics disabled
    result = run_diagnostic_room(input_data, diagnostics_enabled=False)
    
    print(f"Display Text:\n{result.display_text}")
    print(f"Next Action: {result.next_action}")
    print()


def main():
    """Main function to run all examples"""
    print("Diagnostic Room Implementation Examples")
    print("=" * 50)
    print()
    
    basic_usage_example()
    explicit_signals_example()
    diagnostics_disabled_example()
    
    print("All examples completed successfully!")


if __name__ == "__main__":
    main()
