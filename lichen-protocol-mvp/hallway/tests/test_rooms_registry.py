"""
Tests for the rooms registry functionality
"""

import pytest
from unittest.mock import Mock, patch
from ..rooms_registry import get_room_function, list_available_rooms, is_room_available, ROOMS


class TestRoomsRegistry:
    """Test the rooms registry functionality"""
    
    def test_list_available_rooms(self):
        """Test that list_available_rooms returns all registered room IDs"""
        rooms = list_available_rooms()
        expected_rooms = [
            "entry_room", "diagnostic_room", "protocol_room", 
            "walk_room", "memory_room", "integration_commit_room", "exit_room"
        ]
        assert set(rooms) == set(expected_rooms)
    
    def test_is_room_available(self):
        """Test that is_room_available correctly identifies available rooms"""
        assert is_room_available("entry_room") is True
        assert is_room_available("diagnostic_room") is True
        assert is_room_available("nonexistent_room") is False
    
    def test_get_room_function_success(self):
        """Test that get_room_function returns the correct function for valid rooms"""
        room_fn = get_room_function("entry_room")
        assert callable(room_fn)
        assert room_fn in ROOMS.values()
    
    def test_get_room_function_not_found(self):
        """Test that get_room_function raises KeyError for non-existent rooms"""
        with pytest.raises(KeyError, match="Room 'nonexistent_room' not found in registry"):
            get_room_function("nonexistent_room")
    
    def test_rooms_registry_structure(self):
        """Test that the ROOMS registry has the expected structure"""
        assert isinstance(ROOMS, dict)
        assert len(ROOMS) == 7  # All 7 rooms should be registered
        
        # Check that all expected room IDs are present
        expected_room_ids = [
            "entry_room", "diagnostic_room", "protocol_room", 
            "walk_room", "memory_room", "integration_commit_room", "exit_room"
        ]
        for room_id in expected_room_ids:
            assert room_id in ROOMS
            assert callable(ROOMS[room_id])
    
    def test_room_function_calls(self):
        """Test that room functions can be called and are callable"""
        # Get the room function
        room_fn = get_room_function("entry_room")
        
        # Check that it's callable
        assert callable(room_fn)
        
        # Check that it's an async function
        import inspect
        assert inspect.iscoroutinefunction(room_fn)
