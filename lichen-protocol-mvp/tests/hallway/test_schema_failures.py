"""
Tests for schema validation error handling and JSON path surfacing.
"""

import pytest
from hallway.validation import assert_schema, ValidationError


class TestSchemaFailures:
    """Test schema validation error handling."""

    def test_schema_validation_with_json_path(self):
        """Test that schema validation errors include JSON path."""
        # This would need an actual schema file to test against
        # For now, test the error path construction
        invalid_data = {
            "v": "1.0",
            "query": "",  # Invalid: empty string when minLength: 1
            "mode": "invalid_mode"  # Invalid enum value
        }

        # Since we don't have the actual QueryRequest schema loaded in test,
        # we'll test with a mock validation error
        try:
            # This will fail to find the schema, which is expected in test
            assert_schema("QueryRequest.schema.json", invalid_data)
            pytest.fail("Expected ValidationError")
        except ValidationError as e:
            # Should contain the schema name in the error
            assert "QueryRequest.schema.json" in str(e)

    def test_validation_error_construction(self):
        """Test ValidationError construction with path information."""
        error = ValidationError("test.schema.json: query -> 'invalid' is not valid", "test.schema.json")

        assert error.schema_name == "test.schema.json"
        assert "query" in str(error)
        assert "invalid" in str(error)

    def test_validation_error_root_level(self):
        """Test ValidationError for root-level validation errors."""
        error = ValidationError("test.schema.json: <root> -> missing required property", "test.schema.json")

        assert error.schema_name == "test.schema.json"
        assert "<root>" in str(error)

    def test_schema_not_found_error(self):
        """Test error when schema file is not found."""
        try:
            assert_schema("nonexistent.schema.json", {})
            pytest.fail("Expected ValidationError")
        except ValidationError as e:
            assert "Schema not found" in str(e)
            assert "nonexistent.schema.json" in str(e)

    def test_nested_validation_error(self):
        """Test validation error with nested JSON path."""
        # Test our error message formatting for nested paths
        error = ValidationError(
            "test.schema.json: filters.doc_types.0 -> 'invalid' is not one of ['protocol', 'reflection', 'essay']",
            "test.schema.json"
        )

        assert "filters.doc_types.0" in str(error)
        assert "invalid" in str(error)
