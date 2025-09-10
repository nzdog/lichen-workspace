#!/usr/bin/env python3
"""
Test suite for RAG schema validation.
Tests that RAG schemas are valid Draft 2020-12 schemas and that fixtures validate correctly.
"""

import json
import pytest
from pathlib import Path
from jsonschema import Draft202012Validator, ValidationError

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
RAG_SCHEMAS_DIR = PROJECT_ROOT / "contracts" / "rag"
FIXTURES_DIR = PROJECT_ROOT / "fixtures" / "rag"

# RAG schema files to test
RAG_SCHEMAS = [
    "QueryRequest.schema.json",
    "QueryResponse.schema.json", 
    "Error.schema.json",
    "TelemetryEvent.schema.json"
]

class TestRAGSchemas:
    """Test RAG schema validation."""
    
    @pytest.fixture
    def schema_validator(self):
        """Create a Draft 2020-12 validator."""
        return Draft202012Validator
    
    def test_schema_files_exist(self):
        """Test that all RAG schema files exist."""
        for schema_file in RAG_SCHEMAS:
            schema_path = RAG_SCHEMAS_DIR / schema_file
            assert schema_path.exists(), f"RAG schema file not found: {schema_path}"
    
    def test_schemas_are_valid_draft_2020_12(self, schema_validator):
        """Test that all RAG schemas are valid Draft 2020-12 schemas."""
        for schema_file in RAG_SCHEMAS:
            schema_path = RAG_SCHEMAS_DIR / schema_file
            
            with open(schema_path, 'r') as f:
                schema = json.load(f)
            
            # Check that schema specifies Draft 2020-12
            assert '$schema' in schema, f"Schema missing $schema field: {schema_file}"
            assert 'draft/2020-12' in schema['$schema'], f"Schema not Draft 2020-12: {schema_file}"
            
            # Validate the schema itself
            try:
                schema_validator.check_schema(schema)
            except Exception as e:
                pytest.fail(f"Invalid schema {schema_file}: {e}")
    
    def test_query_request_good_fixture(self, schema_validator):
        """Test that QueryRequest good fixture validates."""
        schema_path = RAG_SCHEMAS_DIR / "QueryRequest.schema.json"
        fixture_path = FIXTURES_DIR / "query_request.good.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        # Should not raise any exception
        validator.validate(data)
    
    def test_query_request_bad_fixture(self, schema_validator):
        """Test that QueryRequest bad fixture fails validation."""
        schema_path = RAG_SCHEMAS_DIR / "QueryRequest.schema.json"
        fixture_path = FIXTURES_DIR / "query_request.bad.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        with pytest.raises(ValidationError):
            validator.validate(data)
    
    def test_query_response_good_fixture(self, schema_validator):
        """Test that QueryResponse good fixture validates."""
        schema_path = RAG_SCHEMAS_DIR / "QueryResponse.schema.json"
        fixture_path = FIXTURES_DIR / "query_response.good.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        # Should not raise any exception
        validator.validate(data)
    
    def test_query_response_bad_fixture(self, schema_validator):
        """Test that QueryResponse bad fixture fails validation."""
        schema_path = RAG_SCHEMAS_DIR / "QueryResponse.schema.json"
        fixture_path = FIXTURES_DIR / "query_response.bad.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        with pytest.raises(ValidationError):
            validator.validate(data)
    
    def test_error_good_fixture(self, schema_validator):
        """Test that Error good fixture validates."""
        schema_path = RAG_SCHEMAS_DIR / "Error.schema.json"
        fixture_path = FIXTURES_DIR / "error.good.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        # Should not raise any exception
        validator.validate(data)
    
    def test_error_bad_fixture(self, schema_validator):
        """Test that Error bad fixture fails validation."""
        schema_path = RAG_SCHEMAS_DIR / "Error.schema.json"
        fixture_path = FIXTURES_DIR / "error.bad.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        with pytest.raises(ValidationError):
            validator.validate(data)
    
    def test_telemetry_good_fixture(self, schema_validator):
        """Test that TelemetryEvent good fixture validates."""
        schema_path = RAG_SCHEMAS_DIR / "TelemetryEvent.schema.json"
        fixture_path = FIXTURES_DIR / "telemetry.good.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        # Should not raise any exception
        validator.validate(data)
    
    def test_telemetry_bad_fixture(self, schema_validator):
        """Test that TelemetryEvent bad fixture fails validation."""
        schema_path = RAG_SCHEMAS_DIR / "TelemetryEvent.schema.json"
        fixture_path = FIXTURES_DIR / "telemetry.bad.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        with pytest.raises(ValidationError):
            validator.validate(data)
