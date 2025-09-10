"""End-to-end tests for the processing pipeline."""

import json
import tempfile
from pathlib import Path

import pytest

from src.lichen_chunker.pipeline import create_pipeline
from src.lichen_chunker.embeddings import SBERTEmbedder


def create_test_protocol_file() -> Path:
    """Create a test protocol file."""
    protocol_data = {
        "Title": "Test Protocol",
        "Short Title": "Test",
        "Overall Purpose": "Test purpose",
        "Why This Matters": "Test importance",
        "When To Use This Protocol": "Test usage",
        "Overall Outcomes": {
            "Poor": "Poor outcome",
            "Expected": "Expected outcome",
            "Excellent": "Excellent outcome",
            "Transcendent": "Transcendent outcome"
        },
        "Themes": [
            {
                "Name": "Test Theme",
                "Purpose of This Theme": "Test theme purpose",
                "Why This Matters": "Test theme importance",
                "Outcomes": {
                    "Poor": {
                        "Present pattern": "Poor pattern",
                        "Immediate cost": "Poor cost",
                        "30-90 day system effect": "Poor effect",
                        "Signals": "Poor signals",
                        "Edge condition": "Poor edge",
                        "Example moves": "Poor moves",
                        "Future effect": "Poor future"
                    },
                    "Expected": {
                        "Present pattern": "Expected pattern",
                        "Immediate cost": "Expected cost",
                        "30-90 day system effect": "Expected effect",
                        "Signals": "Expected signals",
                        "Edge condition": "Expected edge",
                        "Example moves": "Expected moves",
                        "Future effect": "Expected future"
                    },
                    "Excellent": {
                        "Present pattern": "Excellent pattern",
                        "Immediate cost": "Excellent cost",
                        "30-90 day system effect": "Excellent effect",
                        "Signals": "Excellent signals",
                        "Edge condition": "Excellent edge",
                        "Example moves": "Excellent moves",
                        "Future effect": "Excellent future"
                    },
                    "Transcendent": {
                        "Present pattern": "Transcendent pattern",
                        "Immediate cost": "Transcendent cost",
                        "30-90 day system effect": "Transcendent effect",
                        "Signals": "Transcendent signals",
                        "Edge condition": "Transcendent edge",
                        "Example moves": "Transcendent moves",
                        "Future effect": "Transcendent future"
                    }
                },
                "Guiding Questions": ["Question 1", "Question 2"]
            }
        ],
        "Completion Prompts": ["Prompt 1", "Prompt 2"]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
        json.dump(protocol_data, tmp_file)
        return Path(tmp_file.name)


def test_pipeline_creation():
    """Test pipeline creation."""
    pipeline = create_pipeline(backend="sbert", max_tokens=100, overlap_tokens=10)
    
    assert pipeline.max_tokens == 100
    assert pipeline.overlap_tokens == 10
    assert pipeline.embedding_backend.name.startswith("sbert")


def test_process_file():
    """Test processing a single file."""
    protocol_file = create_test_protocol_file()
    
    try:
        pipeline = create_pipeline(backend="sbert", max_tokens=100, overlap_tokens=10)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "output"
            
            result = pipeline.process_file(protocol_file, output_dir, protocol_id="test_protocol")
            
            assert result.valid
            assert result.chunks_created > 0
            assert result.chunks_file is not None
            
            # Check that chunks file was created
            chunks_file = Path(result.chunks_file)
            assert chunks_file.exists()
            
            # Check that chunks contain expected content
            with open(chunks_file, 'r') as f:
                chunks = [json.loads(line) for line in f]
            
            assert len(chunks) > 0
            
            # Check chunk structure
            for chunk in chunks:
                assert "text" in chunk
                assert "metadata" in chunk
                assert chunk["metadata"]["protocol_id"] == "test_protocol"
                assert chunk["metadata"]["title"] == "Test Protocol"
    
    finally:
        protocol_file.unlink(missing_ok=True)


def test_search():
    """Test search functionality."""
    protocol_file = create_test_protocol_file()
    
    try:
        pipeline = create_pipeline(backend="sbert", max_tokens=100, overlap_tokens=10)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "output"
            
            # Process file
            result = pipeline.process_file(protocol_file, output_dir, protocol_id="test_protocol")
            assert result.valid
            
            # Save index
            pipeline.save_index()
            
            # Search
            results = pipeline.search("test purpose", k=3)
            
            assert len(results) > 0
            
            # Check search result structure
            for result in results:
                assert result.score > 0
                assert result.text_preview
                # Protocol ID should be either our test protocol, from existing index, or temp file
                assert result.metadata.protocol_id in ["test_protocol", "the_leadership_im_actually_carrying"] or result.metadata.protocol_id.startswith("tmp")
    
    finally:
        protocol_file.unlink(missing_ok=True)


def test_get_stats():
    """Test getting pipeline statistics."""
    pipeline = create_pipeline(backend="sbert")
    
    stats = pipeline.get_stats()
    
    assert "total_chunks" in stats
    assert "embedding_dimension" in stats
    assert "embedding_backend" in stats
    assert "index_path" in stats
    
    assert stats["embedding_backend"].startswith("sbert")
    assert stats["embedding_dimension"] > 0


def test_protocol_id_from_filename():
    """Test protocol_id derived from filename when JSON has auto/temp ID."""
    # Create test protocol with auto ID
    protocol_data = {
        "Title": "The Leadership I'm Actually Carrying",
        "Short Title": "Test",
        "Overall Purpose": "Test purpose",
        "Why This Matters": "Test importance",
        "When To Use This Protocol": "Test usage",
        "Overall Outcomes": {
            "Poor": "Poor outcome",
            "Expected": "Expected outcome",
            "Excellent": "Excellent outcome",
            "Transcendent": "Transcendent outcome"
        },
        "Themes": [
            {
                "Name": "Test Theme",
                "Purpose of This Theme": "Test theme purpose",
                "Why This Matters": "Test theme importance",
                "Outcomes": {
                    "Poor": {
                        "Present pattern": "Poor pattern",
                        "Immediate cost": "Poor cost",
                        "30-90 day system effect": "Poor effect",
                        "Signals": "Poor signals",
                        "Edge condition": "Poor edge",
                        "Example moves": "Poor moves",
                        "Future effect": "Poor future"
                    },
                    "Expected": {
                        "Present pattern": "Expected pattern",
                        "Immediate cost": "Expected cost",
                        "30-90 day system effect": "Expected effect",
                        "Signals": "Expected signals",
                        "Edge condition": "Expected edge",
                        "Example moves": "Expected moves",
                        "Future effect": "Expected future"
                    },
                    "Excellent": {
                        "Present pattern": "Excellent pattern",
                        "Immediate cost": "Excellent cost",
                        "30-90 day system effect": "Excellent effect",
                        "Signals": "Excellent signals",
                        "Edge condition": "Excellent edge",
                        "Example moves": "Excellent moves",
                        "Future effect": "Excellent future"
                    },
                    "Transcendent": {
                        "Present pattern": "Transcendent pattern",
                        "Immediate cost": "Transcendent cost",
                        "30-90 day system effect": "Transcendent effect",
                        "Signals": "Transcendent signals",
                        "Edge condition": "Transcendent edge",
                        "Example moves": "Transcendent moves",
                        "Future effect": "Transcendent future"
                    }
                },
                "Guiding Questions": ["Question 1", "Question 2", "Question 3"]
            }
        ],
        "Completion Prompts": ["Prompt 1", "Prompt 2"],
        "Version": "1.0.0",
        "Created At": "2025-08-19",
        "Protocol ID": "auto_12345_0",  # This should be replaced
        "Category": "strategy-and-growth",
        "Metadata": {
            "Complexity": 1,
            "Readiness Stage": "Explore",
            "Modes": ["Full Walk"],
            "Estimated Time": "10m",
            "Tone Markers": [],
            "Primary Scenarios": [],
            "Related Protocols": [],
            "Tags": []
        }
    }
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / "The Leadership I'm Actually Carrying.json"
        with open(tmp_path, 'w') as f:
            json.dump(protocol_data, f)
    
        pipeline = create_pipeline(backend="sbert", max_tokens=100, overlap_tokens=10)
        
        with tempfile.TemporaryDirectory() as output_tmp_dir:
            output_dir = Path(output_tmp_dir) / "output"
            
            # Process file
            result = pipeline.process_file(tmp_path, output_dir)
            
            assert result.valid
            assert result.chunks_created > 0
            
            # Check that chunks file was created with derived protocol_id
            chunks_file = Path(result.chunks_file)
            assert chunks_file.exists()
            
            # Check that chunks contain expected protocol_id
            with open(chunks_file, 'r') as f:
                chunks = [json.loads(line) for line in f]
            
            assert len(chunks) > 0
            
            # All chunks should have the derived protocol_id
            expected_id = "the_leadership_im_actually_carrying"  # derived from filename
            for chunk in chunks:
                assert chunk["metadata"]["protocol_id"] == expected_id
                assert chunk["metadata"]["chunk_id"].startswith(f"{expected_id}::s")


def test_preserve_clean_explicit_id():
    """Test that clean explicit Protocol IDs are preserved."""
    protocol_data = {
        "Title": "Different Title",
        "Short Title": "Test",
        "Overall Purpose": "Test purpose",
        "Why This Matters": "Test importance",
        "When To Use This Protocol": "Test usage",
        "Overall Outcomes": {
            "Poor": "Poor outcome",
            "Expected": "Expected outcome",
            "Excellent": "Excellent outcome",
            "Transcendent": "Transcendent outcome"
        },
        "Themes": [
            {
                "Name": "Test Theme",
                "Purpose of This Theme": "Test theme purpose",
                "Why This Matters": "Test theme importance",
                "Outcomes": {
                    "Poor": {
                        "Present pattern": "Poor pattern",
                        "Immediate cost": "Poor cost",
                        "30-90 day system effect": "Poor effect",
                        "Signals": "Poor signals",
                        "Edge condition": "Poor edge",
                        "Example moves": "Poor moves",
                        "Future effect": "Poor future"
                    },
                    "Expected": {
                        "Present pattern": "Expected pattern",
                        "Immediate cost": "Expected cost",
                        "30-90 day system effect": "Expected effect",
                        "Signals": "Expected signals",
                        "Edge condition": "Expected edge",
                        "Example moves": "Expected moves",
                        "Future effect": "Expected future"
                    },
                    "Excellent": {
                        "Present pattern": "Excellent pattern",
                        "Immediate cost": "Excellent cost",
                        "30-90 day system effect": "Excellent effect",
                        "Signals": "Excellent signals",
                        "Edge condition": "Excellent edge",
                        "Example moves": "Excellent moves",
                        "Future effect": "Excellent future"
                    },
                    "Transcendent": {
                        "Present pattern": "Transcendent pattern",
                        "Immediate cost": "Transcendent cost",
                        "30-90 day system effect": "Transcendent effect",
                        "Signals": "Transcendent signals",
                        "Edge condition": "Transcendent edge",
                        "Example moves": "Transcendent moves",
                        "Future effect": "Transcendent future"
                    }
                },
                "Guiding Questions": ["Question 1", "Question 2", "Question 3"]
            }
        ],
        "Completion Prompts": ["Prompt 1", "Prompt 2"],
        "Version": "1.0.0",
        "Created At": "2025-08-19",
        "Protocol ID": "my_custom_stable_id",  # This should be preserved
        "Category": "strategy-and-growth",
        "Metadata": {
            "Complexity": 1,
            "Readiness Stage": "Explore",
            "Modes": ["Full Walk"],
            "Estimated Time": "10m",
            "Tone Markers": [],
            "Primary Scenarios": [],
            "Related Protocols": [],
            "Tags": []
        }
    }
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / "different_title.json"
        with open(tmp_path, 'w') as f:
            json.dump(protocol_data, f)
    
        pipeline = create_pipeline(backend="sbert", max_tokens=100, overlap_tokens=10)
        
        with tempfile.TemporaryDirectory() as output_tmp_dir:
            output_dir = Path(output_tmp_dir) / "output"
            
            # Process file
            result = pipeline.process_file(tmp_path, output_dir)
            
            assert result.valid
            assert result.chunks_created > 0
            
            # Check that chunks file was created
            chunks_file = Path(result.chunks_file)
            assert chunks_file.exists()
            
            # Check that chunks contain expected protocol_id
            with open(chunks_file, 'r') as f:
                chunks = [json.loads(line) for line in f]
            
            assert len(chunks) > 0
            
            # All chunks should preserve the clean explicit protocol_id
            for chunk in chunks:
                assert chunk["metadata"]["protocol_id"] == "my_custom_stable_id"
                assert chunk["metadata"]["chunk_id"].startswith("my_custom_stable_id::s")
