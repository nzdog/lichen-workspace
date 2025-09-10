"""
Tests for the schema utilities functionality
"""

import pytest
import json
import os
import tempfile
from unittest.mock import patch, mock_open
from ..schema_utils import (
    validate_or_decline, 
    get_room_schema_path, 
    validate_room_output, 
    create_schema_decline
)


class TestSchemaUtils:
    """Test the schema utilities functionality"""
    
    def test_create_schema_decline(self):
        """Test that create_schema_decline creates proper decline objects"""
        decline = create_schema_decline("test_room", "Validation error message")
        
        assert decline["display_text"] == "Schema validation failed for test_room: Validation error message"
        assert decline["next_action"] == "hold"
        assert decline["_decline_reason"] == "schema_validation_failed"
        assert decline["_error_details"] == "Validation error message"
    
    def test_get_room_schema_path(self):
        """Test that get_room_schema_path returns correct paths"""
        path = get_room_schema_path("entry_room")
        expected_filename = "entry_room.schema.json"
        assert path.endswith(expected_filename)
        assert "room_schemas" in path
    
    def test_validate_or_decline_success(self):
        """Test successful validation"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name", "age"]
        }
        
        obj = {"name": "John", "age": 30}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema, f)
            schema_path = f.name
        
        try:
            is_valid, error = validate_or_decline(obj, schema_path)
            assert is_valid is True
            assert error is None
        finally:
            os.unlink(schema_path)
    
    def test_validate_or_decline_failure(self):
        """Test validation failure"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name", "age"]
        }
        
        obj = {"name": "John"}  # Missing required 'age' field
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema, f)
            schema_path = f.name
        
        try:
            is_valid, error = validate_or_decline(obj, schema_path)
            assert is_valid is False
            assert "age" in error
            assert "required" in error
        finally:
            os.unlink(schema_path)
    
    def test_validate_or_decline_schema_not_found(self):
        """Test validation when schema file doesn't exist"""
        is_valid, error = validate_or_decline({}, "/nonexistent/schema.json")
        assert is_valid is False
        assert "not found" in error
    
    def test_validate_room_output_success(self):
        """Test successful room output validation"""
        room_output = {
            "display_text": "Hello world",
            "next_action": "continue"
        }
        
        # Mock the schema validation to succeed
        with patch('hallway.schema_utils.validate_or_decline') as mock_validate:
            mock_validate.return_value = (True, None)
            
            is_valid, error = validate_room_output("entry_room", room_output)
            assert is_valid is True
            assert error is None
    
    def test_validate_room_output_failure(self):
        """Test room output validation failure"""
        room_output = {
            "display_text": "Hello world"
            # Missing required 'next_action' field
        }
        
        # Mock the schema validation to fail
        with patch('hallway.schema_utils.validate_or_decline') as mock_validate:
            mock_validate.return_value = (False, "Missing required field: next_action")
            
            is_valid, error = validate_room_output("entry_room", room_output)
            assert is_valid is False
            assert "Missing required field: next_action" in error
    
    def test_validate_or_decline_invalid_schema(self):
        """Test validation with invalid schema"""
        invalid_schema = {
            "type": "invalid_type"  # Invalid JSON Schema type
        }
        
        obj = {"test": "value"}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_schema, f)
            schema_path = f.name
        
        try:
            is_valid, error = validate_or_decline(obj, schema_path)
            assert is_valid is False
            assert "error" in error.lower()
        finally:
            os.unlink(schema_path)
