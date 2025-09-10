"""
Exit Room Example Usage
Demonstrates the Exit Room functionality with various scenarios
"""

from .exit_room import ExitRoom, run_exit_room
from .contract_types import ExitRoomInput, ExitReason


def example_normal_completion():
    """Example of normal session completion"""
    print("=== Normal Session Completion Example ===")
    
    # Create exit room
    room = ExitRoom()
    
    # Prepare input for normal completion
    input_data = ExitRoomInput(
        session_state_ref="session_123",
        payload={
            "completion_confirmed": True,
            "session_goals_met": True,
            "integration_complete": True,
            "commitments_recorded": True,
            "reflection_done": True,
            "completion_quality": "comprehensive"
        }
    )
    
    # Process exit
    result = room.process_exit(input_data)
    
    print(f"Next Action: {result.next_action}")
    print("\nDisplay Text:")
    print(result.display_text)
    
    # Show room status
    print("\nRoom Status:")
    status = room.get_room_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    return result


def example_basic_completion():
    """Example of basic completion"""
    print("\n=== Basic Completion Example ===")
    
    # Create exit room
    room = ExitRoom()
    
    # Prepare input for basic completion
    input_data = ExitRoomInput(
        session_state_ref="session_456",
        payload={
            "completion_confirmed": True,
            "session_goals_met": True,
            "completion_quality": "basic"
        }
    )
    
    # Process exit
    result = room.process_exit(input_data)
    
    print(f"Next Action: {result.next_action}")
    print("\nDisplay Text:")
    print(result.display_text)
    
    return result


def example_force_exit():
    """Example of force exit (bypasses completion)"""
    print("\n=== Force Exit Example ===")
    
    # Create exit room
    room = ExitRoom()
    
    # Prepare input for force exit
    input_data = ExitRoomInput(
        session_state_ref="session_789",
        payload={
            "exit_reason": "force_closed",
            "force_exit": True,
            "completion_confirmed": False
        }
    )
    
    # Process exit
    result = room.process_exit(input_data)
    
    print(f"Next Action: {result.next_action}")
    print("\nDisplay Text:")
    print(result.display_text)
    
    return result


def example_completion_failure():
    """Example of completion requirement failure"""
    print("\n=== Completion Failure Example ===")
    
    # Create exit room
    room = ExitRoom()
    
    # Prepare input that will fail completion
    input_data = ExitRoomInput(
        session_state_ref="session_fail",
        payload={
            "completion_confirmed": False,
            "session_goals_met": False
        }
    )
    
    # Process exit
    result = room.process_exit(input_data)
    
    print(f"Next Action: {result.next_action}")
    print("\nDisplay Text:")
    print(result.display_text)
    
    return result


def example_error_condition():
    """Example of error condition exit"""
    print("\n=== Error Condition Exit Example ===")
    
    # Create exit room
    room = ExitRoom()
    
    # Prepare input for error condition
    input_data = ExitRoomInput(
        session_state_ref="session_error",
        payload={
            "exit_reason": "error_condition",
            "has_errors": True,
            "errors": ["Connection timeout", "Data validation failed"]
        }
    )
    
    # Process exit
    result = room.process_exit(input_data)
    
    print(f"Next Action: {result.next_action}")
    print("\nDisplay Text:")
    print(result.display_text)
    
    return result


def example_session_reentry():
    """Example of session re-entry after exit"""
    print("\n=== Session Re-entry Example ===")
    
    # Create exit room
    room = ExitRoom()
    
    # First, complete a session
    input_data = ExitRoomInput(
        session_state_ref="session_reentry",
        payload={
            "completion_confirmed": True,
            "session_goals_met": True
        }
    )
    
    result = room.process_exit(input_data)
    print("First exit completed successfully")
    
    # Check if session can be re-entered
    session_status = room.get_session_status("session_reentry")
    if session_status:
        print(f"\nSession Status After Exit:")
        for key, value in session_status.items():
            print(f"  {key}: {value}")
    
    # Try to re-enter the same session
    print("\nAttempting to re-enter session...")
    reentry_result = room.process_exit(input_data)
    
    print(f"Re-entry Result - Next Action: {reentry_result.next_action}")
    print("\nDisplay Text:")
    print(reentry_result.display_text)
    
    return reentry_result


def run_all_examples():
    """Run all examples"""
    print("🚪 Exit Room Examples")
    print("=" * 50)
    
    try:
        # Run all examples
        example_normal_completion()
        example_basic_completion()
        example_force_exit()
        example_completion_failure()
        example_error_condition()
        example_session_reentry()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Example failed: {str(e)}")


if __name__ == "__main__":
    run_all_examples()
