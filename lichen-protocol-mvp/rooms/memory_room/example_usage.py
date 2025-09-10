#!/usr/bin/env python3
"""
Memory Room Example Usage
Demonstrates the core functionality of the Memory Room implementation.
"""

from rooms.memory_room import MemoryRoom, run_memory_room
from rooms.memory_room.contract_types import MemoryRoomInput


def demonstrate_memory_capture():
    """Demonstrate memory capture functionality"""
    print("=== Memory Capture Demo ===")
    
    # Create memory room instance
    room = MemoryRoom()
    
    # Capture memory with tone and residue
    capture_input = MemoryRoomInput(
        session_state_ref="demo-session-1",
        payload={
            "tone_label": "calm",
            "residue_label": "peaceful",
            "readiness_state": "ready",
            "integration_notes": "feeling centered after morning meditation",
            "commitments": "practice daily grounding exercises"
        }
    )
    
    result = room.run_memory_room(capture_input)
    print("Capture Result:")
    print(result.display_text)
    print()
    
    return room


def demonstrate_user_control(room):
    """Demonstrate user control operations"""
    print("=== User Control Demo ===")
    
    # Get the captured item ID
    session = room._get_or_create_session("demo-session-1")
    item_id = session.items[0].item_id
    
    # Pin the item
    pin_input = MemoryRoomInput(
        session_state_ref="demo-session-1",
        payload={"action": "pin", "item_id": item_id}
    )
    
    result = room.run_memory_room(pin_input)
    print("Pin Result:")
    print(result.display_text)
    print()
    
    # Edit the item
    edit_input = MemoryRoomInput(
        session_state_ref="demo-session-1",
        payload={
            "action": "edit",
            "item_id": item_id,
            "field_name": "commitments",
            "new_value": "practice daily grounding exercises and evening reflection"
        }
    )
    
    result = room.run_memory_room(edit_input)
    print("Edit Result:")
    print(result.display_text)
    print()


def demonstrate_memory_retrieval(room):
    """Demonstrate memory retrieval functionality"""
    print("=== Memory Retrieval Demo ===")
    
    # Retrieve session-scoped memory
    retrieve_input = MemoryRoomInput(
        session_state_ref="demo-session-1",
        payload={"scope": "session"}
    )
    
    result = room.run_memory_room(retrieve_input)
    print("Session Retrieval Result:")
    print(result.display_text)
    print()
    
    # Get memory summary
    summary_input = MemoryRoomInput(
        session_state_ref="demo-session-1",
        payload={"summary": True}
    )
    
    result = room.run_memory_room(summary_input)
    print("Memory Summary Result:")
    print(result.display_text)
    print()


def demonstrate_continuity_across_rooms(room):
    """Demonstrate memory continuity for downstream rooms"""
    print("=== Memory Continuity Demo ===")
    
    # Get memory context for a downstream room
    context = room.get_memory_for_room(
        room_id="diagnostic_room",
        session_id="demo-session-1"
    )
    
    print("Memory Context for Diagnostic Room:")
    print(f"Session Context: {context['session_context']['summary']}")
    print(f"Global Context: {context['global_context']['summary']}")
    print(f"Overall Summary: {context['summary']}")
    print()


def demonstrate_governance_compliance(room):
    """Demonstrate governance compliance checking"""
    print("=== Governance Compliance Demo ===")
    
    # Get session stats including governance compliance
    session_stats = room.get_session_stats("demo-session-1")
    
    print("Session Statistics:")
    print(f"Total Items: {session_stats['total_items']}")
    print(f"Active Items: {session_stats['active_items']}")
    print(f"Pinned Items: {session_stats['pinned_items']}")
    print()


def demonstrate_error_handling():
    """Demonstrate error handling and graceful degradation"""
    print("=== Error Handling Demo ===")
    
    room = MemoryRoom()
    
    # Try to pin a non-existent item
    pin_input = MemoryRoomInput(
        session_state_ref="error-session",
        payload={"action": "pin", "item_id": "nonexistent-id"}
    )
    
    result = room.run_memory_room(pin_input)
    print("Error Handling Result:")
    print(result.display_text)
    print()
    
    # Try to edit with invalid field
    edit_input = MemoryRoomInput(
        session_state_ref="error-session",
        payload={
            "action": "edit",
            "item_id": "some-id",
            "field_name": "invalid_field",
            "new_value": "some value"
        }
    )
    
    result = room.run_memory_room(edit_input)
    print("Invalid Field Error Result:")
    print(result.display_text)
    print()


def main():
    """Run all demonstration functions"""
    print("Memory Room Implementation Demo")
    print("=" * 50)
    print()
    
    # Run demonstrations
    room = demonstrate_memory_capture()
    demonstrate_user_control(room)
    demonstrate_memory_retrieval(room)
    demonstrate_continuity_across_rooms(room)
    demonstrate_governance_compliance(room)
    demonstrate_error_handling()
    
    print("=== Demo Complete ===")
    print("All Memory Room functionality demonstrated successfully!")


if __name__ == "__main__":
    main()
