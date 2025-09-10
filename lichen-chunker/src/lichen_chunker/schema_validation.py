"""JSON schema validation for Lichen Protocol files."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError

from .types import Protocol


class ValidationError(Exception):
    """Custom validation error with detailed information."""
    
    def __init__(self, message: str, errors: List[JsonSchemaValidationError]):
        super().__init__(message)
        self.errors = errors


def load_schema(schema_path: Path) -> Dict[str, Any]:
    """Load JSON schema from file."""
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_protocol_json(
    protocol_data: Dict[str, Any], 
    schema_path: Optional[Path] = None
) -> Tuple[bool, List[str]]:
    """
    Validate protocol JSON against schema.
    
    Args:
        protocol_data: The protocol data to validate
        schema_path: Path to schema file (uses default if None)
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    if schema_path is None:
        schema_path = Path(__file__).parent.parent.parent / "libs" / "protocol_template_schema_v1.json"
    
    schema = load_schema(schema_path)
    validator = jsonschema.Draft7Validator(schema)
    
    errors = []
    for error in validator.iter_errors(protocol_data):
        error_msg = _format_validation_error(error)
        errors.append(error_msg)
    
    return len(errors) == 0, errors


def _format_validation_error(error: JsonSchemaValidationError) -> str:
    """Format a validation error into a readable message."""
    path = " -> ".join(str(p) for p in error.absolute_path)
    if path:
        location = f"at '{path}'"
    else:
        location = "at root level"
    
    if error.validator == "required":
        missing = ", ".join(f"'{field}'" for field in error.validator_value)
        return f"Missing required fields {missing} {location}"
    elif error.validator == "type":
        expected = error.validator_value
        actual = type(error.instance).__name__
        return f"Expected {expected}, got {actual} {location}"
    elif error.validator == "minLength":
        return f"String too short (minimum {error.validator_value} characters) {location}"
    elif error.validator == "minItems":
        return f"Array too short (minimum {error.validator_value} items) {location}"
    elif error.validator == "additionalProperties":
        if error.validator_value is False:
            extra = ", ".join(f"'{prop}'" for prop in error.validator_value)
            return f"Additional properties not allowed: {extra} {location}"
    else:
        return f"Validation error: {error.message} {location}"


def validate_protocol_file(
    file_path: Path, 
    schema_path: Optional[Path] = None
) -> Tuple[bool, List[str], Optional[Dict[str, Any]]]:
    """
    Validate a protocol file.
    
    Args:
        file_path: Path to the protocol JSON file
        schema_path: Path to schema file (uses default if None)
        
    Returns:
        Tuple of (is_valid, error_messages, parsed_data)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            protocol_data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"], None
    except Exception as e:
        return False, [f"Error reading file: {e}"], None
    
    is_valid, errors = validate_protocol_json(protocol_data, schema_path)
    return is_valid, errors, protocol_data if is_valid else None


def validate_and_parse_protocol(
    file_path: Path, 
    schema_path: Optional[Path] = None
) -> Tuple[bool, List[str], Optional[Protocol]]:
    """
    Validate and parse a protocol file into a Protocol object.
    
    Args:
        file_path: Path to the protocol JSON file
        schema_path: Path to schema file (uses default if None)
        
    Returns:
        Tuple of (is_valid, error_messages, parsed_protocol)
    """
    is_valid, errors, protocol_data = validate_protocol_file(file_path, schema_path)
    
    if not is_valid:
        return False, errors, None
    
    try:
        protocol = Protocol(**protocol_data)
        return True, [], protocol
    except Exception as e:
        return False, [f"Error parsing protocol: {e}"], None


def normalize_protocol_data(protocol_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize protocol data to handle common variations.
    
    This function handles common mistakes like single strings vs arrays
    and ensures consistent structure.
    """
    normalized = protocol_data.copy()
    
    # Normalize completion prompts to array if it's a string
    if "Completion Prompts" in normalized:
        if isinstance(normalized["Completion Prompts"], str):
            normalized["Completion Prompts"] = [normalized["Completion Prompts"]]
    
    # Normalize guiding questions in themes
    if "Themes" in normalized:
        for theme in normalized["Themes"]:
            if "Guiding Questions" in theme:
                if isinstance(theme["Guiding Questions"], str):
                    theme["Guiding Questions"] = [theme["Guiding Questions"]]
    
    # Normalize metadata arrays
    if "Metadata" in normalized:
        metadata = normalized["Metadata"]
        array_fields = ["Modes", "Tone Markers", "Primary Scenarios", "Related Protocols", "Tags", "Stones", "Fields", "Bridges"]
        for field in array_fields:
            if field in metadata and isinstance(metadata[field], str):
                metadata[field] = [metadata[field]]
    
    return normalized