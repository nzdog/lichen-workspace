"""
Schema Utilities for Hallway Orchestrator
Provides validation and decline conversion utilities
"""

import json
import os
from typing import Dict, Any, Tuple, Optional
from jsonschema import validate, ValidationError

def validate_or_decline(obj: Dict[str, Any], schema_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an object against a JSON schema.
    
    Args:
        obj: The object to validate
        schema_path: Path to the JSON schema file
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if validation passes, False otherwise
        - error_message: Description of validation error if failed, None if passed
    """
    try:
        # Load the schema
        if not os.path.exists(schema_path):
            return False, f"Schema file not found: {schema_path}"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        # Validate the object
        validate(instance=obj, schema=schema)
        return True, None
        
    except ValidationError as e:
        # Extract meaningful error message
        error_path = " -> ".join(str(p) for p in e.path) if e.path else "root"
        return False, f"Schema validation failed at {error_path}: {e.message}"
        
    except Exception as e:
        return False, f"Unexpected error during validation: {str(e)}"

def get_room_schema_path(room_id: str) -> str:
    """
    Get the schema path for a specific room.
    
    Args:
        room_id: The room identifier
        
    Returns:
        Path to the room's schema file
    """
    return os.path.join(os.path.dirname(__file__), "room_schemas", f"{room_id}.schema.json")

def validate_room_output(room_id: str, room_output: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate a room's output against its schema.
    
    Args:
        room_id: The room identifier
        room_output: The room's output to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    schema_path = get_room_schema_path(room_id)
    return validate_or_decline(room_output, schema_path)

def create_schema_decline(room_id: str, validation_error: str) -> Dict[str, Any]:
    """
    Create a structured decline for schema validation failures.
    
    Args:
        room_id: The room identifier
        validation_error: The validation error message
        
    Returns:
        A structured decline object
    """
    return {
        "display_text": f"Schema validation failed for {room_id}: {validation_error}",
        "next_action": "hold",
        "_decline_reason": "schema_validation_failed",
        "_error_details": validation_error
    }
