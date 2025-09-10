"""
Schema validation boundaries with caching and helpful error messages.
"""

import json
import os
from functools import lru_cache
from typing import Any, Dict
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError as JsonSchemaValidationError
from .errors import ValidationError


@lru_cache(maxsize=32)
def _load_schema(schema_name: str) -> Dict[str, Any]:
    """Load and cache a JSON schema by name."""
    # Look in contracts directory relative to project root
    project_root = Path(__file__).parent.parent
    schema_paths = [
        project_root / "contracts" / "rooms" / schema_name,
        project_root / "contracts" / "gates" / schema_name,
        project_root / "contracts" / "rag" / schema_name,
        project_root / "contracts" / "rag_build" / schema_name,
        project_root / "contracts" / "services" / schema_name,
        project_root / "contracts" / "schema" / schema_name,
    ]

    for schema_path in schema_paths:
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                return json.load(f)

    raise ValidationError(f"Schema not found: {schema_name}", schema_name)


def assert_schema(schema_name: str, data: Any) -> None:
    """
    Validate data against a JSON schema.

    Args:
        schema_name: Name of the schema file (e.g., "QueryRequest.schema.json")
        data: Data to validate

    Raises:
        ValidationError: If validation fails
    """
    try:
        schema = _load_schema(schema_name)
        errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: e.path)
        if errors:
            e = errors[0]
            path = ".".join(map(str, e.path))
            raise ValidationError(f"{schema_name}: {path or '<root>'} -> {e.message}", schema_name)
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Schema validation failed: {str(e)}", schema_name) from e


def validate_room_input(room_id: str, data: Any) -> None:
    """Validate room input data."""
    schema_name = f"{room_id}.Input.schema.json"
    assert_schema(schema_name, data)


def validate_room_output(room_id: str, data: Any) -> None:
    """Validate room output data."""
    schema_name = f"{room_id}.Output.schema.json"
    assert_schema(schema_name, data)


def validate_gate_input(gate_name: str, data: Any) -> None:
    """Validate gate input data."""
    schema_name = f"{gate_name}.Input.schema.json"
    assert_schema(schema_name, data)


def validate_gate_output(gate_name: str, data: Any) -> None:
    """Validate gate output data."""
    schema_name = f"{gate_name}.Output.schema.json"
    assert_schema(schema_name, data)


def validate_final_output(data: Any) -> None:
    """Validate final hallway output."""
    assert_schema("HallwayOutput.schema.json", data)
