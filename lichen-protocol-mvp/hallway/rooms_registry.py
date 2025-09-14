"""
Rooms Registry for Hallway Orchestrator
Maps contract room_id to callable async run functions
"""

import asyncio
from typing import Dict, Any, Callable, Awaitable

# Import the real room run functions (no side effects)
try:
    from rooms.entry_room import run_entry_room
    from rooms.diagnostic_room import run_diagnostic_room
    from rooms.protocol_room import run_protocol_room
    from rooms.walk_room import run_walk_room
    from rooms.memory_room import run_memory_room
    from rooms.integration_commit_room import run_integration_commit_room
    from rooms.exit_room import run_exit_room
    from rooms.ai_room import run_ai_room
except ImportError as e:
    # Fallback for testing or when rooms are not available
    print(f"Warning: Could not import room modules: {e}")
    
    # Mock functions for fallback
    async def mock_run(input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "display_text": "Mock room output - room not available",
            "next_action": "continue"
        }
    
    run_entry_room = mock_run
    run_diagnostic_room = mock_run
    run_protocol_room = mock_run
    run_walk_room = mock_run
    run_memory_room = mock_run
    run_integration_commit_room = mock_run
    run_exit_room = mock_run
    run_ai_room = mock_run

# Registry mapping contract room_id to callable async run functions
ROOMS: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {
    "entry_room": run_entry_room,
    "diagnostic_room": run_diagnostic_room,
    "protocol_room": run_protocol_room,
    "walk_room": run_walk_room,
    "memory_room": run_memory_room,
    "integration_commit_room": run_integration_commit_room,
    "exit_room": run_exit_room,
    "ai_room": run_ai_room,
}

def get_room_function(room_id: str) -> Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]:
    """Get the run function for a specific room"""
    if room_id not in ROOMS:
        raise KeyError(f"Room '{room_id}' not found in registry. Available rooms: {list(ROOMS.keys())}")
    return ROOMS[room_id]

def list_available_rooms() -> list[str]:
    """List all available room IDs"""
    return list(ROOMS.keys())

def is_room_available(room_id: str) -> bool:
    """Check if a room is available in the registry"""
    return room_id in ROOMS
