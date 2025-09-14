#!/usr/bin/env python3
"""
Test suite for RAG build schema validation.
Tests that RAG build schemas are valid Draft 2020-12 schemas and that fixtures validate correctly.
"""

import json
import pytest
from pathlib import Path
from jsonschema import Draft202012Validator, ValidationError

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
RAG_BUILD_SCHEMAS_DIR = PROJECT_ROOT / "contracts" / "rag_build"
FIXTURES_DIR = PROJECT_ROOT / "fixtures" / "rag_build"

# RAG build schema files to test
RAG_BUILD_SCHEMAS = [
    "CorpusDoc.schema.json",
    "Chunk.schema.json",
    "EmbeddingJob.schema.json",
    "IndexConfig.schema.json"
]

class TestRAGBuildSchemas:
    """Test RAG build schema validation."""
    
    @pytest.fixture
    def schema_validator(self):
        """Create a Draft 2020-12 validator."""
        return Draft202012Validator
    
    def test_schema_files_exist(self):
        """Test that all RAG build schema files exist."""
        for schema_file in RAG_BUILD_SCHEMAS:
            schema_path = RAG_BUILD_SCHEMAS_DIR / schema_file
            assert schema_path.exists(), f"RAG build schema file not found: {schema_path}"
    
    def test_schemas_are_valid_draft_2020_12(self, schema_validator):
        """Test that all RAG build schemas are valid Draft 2020-12 schemas."""
        for schema_file in RAG_BUILD_SCHEMAS:
            schema_path = RAG_BUILD_SCHEMAS_DIR / schema_file
            
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
    
    def test_corpus_doc_good_fixture(self, schema_validator):
        """Test that CorpusDoc good fixture validates."""
        schema_path = RAG_BUILD_SCHEMAS_DIR / "CorpusDoc.schema.json"
        fixture_path = FIXTURES_DIR / "corpus_doc.good.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        # Should not raise any exception
        validator.validate(data)
    
    def test_corpus_doc_bad_fixture(self, schema_validator):
        """Test that CorpusDoc bad fixture fails validation."""
        schema_path = RAG_BUILD_SCHEMAS_DIR / "CorpusDoc.schema.json"
        fixture_path = FIXTURES_DIR / "corpus_doc.bad.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        with pytest.raises(ValidationError):
            validator.validate(data)
    
    def test_chunk_good_fixture(self, schema_validator):
        """Test that Chunk good fixture validates."""
        schema_path = RAG_BUILD_SCHEMAS_DIR / "Chunk.schema.json"
        fixture_path = FIXTURES_DIR / "chunk.good.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        # Should not raise any exception
        validator.validate(data)
    
    def test_chunk_bad_fixture(self, schema_validator):
        """Test that Chunk bad fixture fails validation."""
        schema_path = RAG_BUILD_SCHEMAS_DIR / "Chunk.schema.json"
        fixture_path = FIXTURES_DIR / "chunk.bad.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        with pytest.raises(ValidationError):
            validator.validate(data)
    
    def test_embedding_job_good_fixture(self, schema_validator):
        """Test that EmbeddingJob good fixture validates."""
        schema_path = RAG_BUILD_SCHEMAS_DIR / "EmbeddingJob.schema.json"
        fixture_path = FIXTURES_DIR / "embedding_job.good.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        # Should not raise any exception
        validator.validate(data)
    
    def test_embedding_job_bad_fixture(self, schema_validator):
        """Test that EmbeddingJob bad fixture fails validation."""
        schema_path = RAG_BUILD_SCHEMAS_DIR / "EmbeddingJob.schema.json"
        fixture_path = FIXTURES_DIR / "embedding_job.bad.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        with pytest.raises(ValidationError):
            validator.validate(data)
    
    def test_index_config_good_fixture(self, schema_validator):
        """Test that IndexConfig good fixture validates."""
        schema_path = RAG_BUILD_SCHEMAS_DIR / "IndexConfig.schema.json"
        fixture_path = FIXTURES_DIR / "index_config.good.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        # Should not raise any exception
        validator.validate(data)
    
    def test_index_config_bad_fixture(self, schema_validator):
        """Test that IndexConfig bad fixture fails validation."""
        schema_path = RAG_BUILD_SCHEMAS_DIR / "IndexConfig.schema.json"
        fixture_path = FIXTURES_DIR / "index_config.bad.json"
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(fixture_path, 'r') as f:
            data = json.load(f)
        
        validator = schema_validator(schema)
        with pytest.raises(ValidationError):
            validator.validate(data)
