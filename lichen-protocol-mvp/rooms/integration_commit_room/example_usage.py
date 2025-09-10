#!/usr/bin/env python3
"""
Integration & Commit Room Example Usage
Demonstrates the core functionality of the Integration & Commit Room implementation.
"""

from rooms.integration_commit_room import IntegrationCommitRoom, run_integration_commit_room
from rooms.integration_commit_room.contract_types import IntegrationCommitRoomInput


def demonstrate_integration_capture():
    """Demonstrate integration data capture"""
    print("=== Integration Capture Demo ===")
    
    # Create integration commit room instance
    room = IntegrationCommitRoom()
    
    # Capture integration data
    integration_input = IntegrationCommitRoomInput(
        session_state_ref="demo-session-1",
        payload={
            "integration_notes": "Feeling more grounded and centered after the morning meditation session. Noticed increased awareness of breath and body sensations.",
            "session_context": "Morning meditation practice focusing on breath awareness and body scanning",
            "key_insights": [
                "Breath awareness helps ground attention",
                "Body scanning reveals tension patterns",
                "Morning practice sets positive tone for day"
            ],
            "shifts_noted": [
                "From scattered to focused attention",
                "From tense to relaxed body state",
                "From rushed to present mindset"
            ]
        }
    )
    
    result = room.run_integration_commit_room(integration_input)
    print("Integration Result:")
    print(result.display_text)
    print()
    
    return room


def demonstrate_commitment_recording(room):
    """Demonstrate commitment recording"""
    print("=== Commitment Recording Demo ===")
    
    # Record commitments with pace states
    commitments_input = IntegrationCommitRoomInput(
        session_state_ref="demo-session-1",
        payload={
            "commitments": [
                {
                    "text": "Practice daily morning meditation for 15 minutes",
                    "context": "Morning routine before breakfast",
                    "pace_state": "NOW",
                    "session_ref": "demo-session-1"
                },
                {
                    "text": "Read mindfulness book for 30 minutes",
                    "context": "Evening wind-down routine",
                    "pace_state": "LATER",
                    "session_ref": "demo-session-1"
                },
                {
                    "text": "Schedule weekly meditation group session",
                    "context": "Community practice and support",
                    "pace_state": "HOLD",
                    "session_ref": "demo-session-1"
                }
            ]
        }
    )
    
    result = room.run_integration_commit_room(commitments_input)
    print("Commitments Result:")
    print(result.display_text)
    print()


def demonstrate_room_completion(room):
    """Demonstrate room completion and memory write"""
    print("=== Room Completion Demo ===")
    
    # Complete the room (write to memory)
    completion_input = IntegrationCommitRoomInput(
        session_state_ref="demo-session-1",
        payload={"complete": True}
    )
    
    result = room.run_integration_commit_room(completion_input)
    print("Completion Result:")
    print(result.display_text)
    print()
    
    print(f"Next Action: {result.next_action}")
    print()


def demonstrate_status_checking(room):
    """Demonstrate status checking"""
    print("=== Status Check Demo ===")
    
    # Check room status
    status_input = IntegrationCommitRoomInput(
        session_state_ref="demo-session-1",
        payload={"status": True}
    )
    
    result = room.run_integration_commit_room(status_input)
    print("Status Result:")
    print(result.display_text)
    print()


def demonstrate_error_handling():
    """Demonstrate error handling and validation"""
    print("=== Error Handling Demo ===")
    
    room = IntegrationCommitRoom()
    
    # Try to record commitments without integration
    commitments_input = IntegrationCommitRoomInput(
        session_state_ref="error-session",
        payload={
            "commitments": [
                {
                    "text": "Practice meditation",
                    "context": "Daily routine",
                    "pace_state": "NOW",
                    "session_ref": "error-session"
                }
            ]
        }
    )
    
    result = room.run_integration_commit_room(commitments_input)
    print("Error Handling Result:")
    print(result.display_text)
    print()
    
    # Try to complete room without requirements
    completion_input = IntegrationCommitRoomInput(
        session_state_ref="error-session",
        payload={"complete": True}
    )
    
    result = room.run_integration_commit_room(completion_input)
    print("Completion Error Result:")
    print(result.display_text)
    print()


def demonstrate_pace_enforcement():
    """Demonstrate pace state enforcement"""
    print("=== Pace Enforcement Demo ===")
    
    room = IntegrationCommitRoom()
    
    # First capture integration
    integration_input = IntegrationCommitRoomInput(
        session_state_ref="pace-demo-session",
        payload={
            "integration_notes": "Feeling energized and ready to take action",
            "session_context": "Afternoon productivity session"
        }
    )
    room.run_integration_commit_room(integration_input)
    
    # Try to record commitment without pace state
    invalid_commitment_input = IntegrationCommitRoomInput(
        session_state_ref="pace-demo-session",
        payload={
            "commitments": [
                {
                    "text": "Complete project proposal",
                    "context": "Work task",
                    "session_ref": "pace-demo-session"
                    # Missing pace_state
                }
            ]
        }
    )
    
    result = room.run_integration_commit_room(invalid_commitment_input)
    print("Pace Enforcement Error Result:")
    print(result.display_text)
    print()


def demonstrate_memory_write():
    """Demonstrate memory write functionality"""
    print("=== Memory Write Demo ===")
    
    room = IntegrationCommitRoom()
    
    # Complete a full session
    integration_input = IntegrationCommitRoomInput(
        session_state_ref="memory-demo-session",
        payload={
            "integration_notes": "Session provided clarity on next steps",
            "session_context": "Weekly planning session"
        }
    )
    room.run_integration_commit_room(integration_input)
    
    commitments_input = IntegrationCommitRoomInput(
        session_state_ref="memory-demo-session",
        payload={
            "commitments": [
                {
                    "text": "Review quarterly goals",
                    "context": "Strategic planning",
                    "pace_state": "NOW",
                    "session_ref": "memory-demo-session"
                }
            ]
        }
    )
    room.run_integration_commit_room(commitments_input)
    
    # Complete and write to memory
    completion_input = IntegrationCommitRoomInput(
        session_state_ref="memory-demo-session",
        payload={"complete": True}
    )
    
    result = room.run_integration_commit_room(completion_input)
    print("Memory Write Result:")
    print(result.display_text)
    print()
    
    # Check memory statistics
    memory_stats = room.memory_write.get_memory_statistics()
    print("Memory Statistics:")
    print(f"Total Sessions: {memory_stats['total_sessions']}")
    print(f"Total Writes: {memory_stats['total_writes']}")
    print(f"Success Rate: {memory_stats['success_rate']:.1%}")
    print()


def main():
    """Run all demonstration functions"""
    print("Integration & Commit Room Implementation Demo")
    print("=" * 60)
    print()
    
    # Run demonstrations
    room = demonstrate_integration_capture()
    demonstrate_commitment_recording(room)
    demonstrate_room_completion(room)
    demonstrate_status_checking(room)
    demonstrate_error_handling()
    demonstrate_pace_enforcement()
    demonstrate_memory_write()
    
    print("=== Demo Complete ===")
    print("All Integration & Commit Room functionality demonstrated successfully!")
    print()
    print("Key Features Demonstrated:")
    print("✅ Integration capture enforcement")
    print("✅ Commitment structure validation")
    print("✅ Pace state enforcement")
    print("✅ Atomic memory write")
    print("✅ Completion requirement validation")
    print("✅ Error handling and graceful degradation")


if __name__ == "__main__":
    main()
