"""
Tests for grounding score computation in indexer.
"""

import pytest
import numpy as np
import tempfile
import json
from pathlib import Path

# Add the src directory to the path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from indexer import IndexBuilder


class TestGroundingScoreComputation:
    """Test grounding score computation in IndexBuilder."""
    
    def test_compute_grounding_scores_basic(self):
        """Test basic grounding score computation."""
        builder = IndexBuilder({})
        
        vectors = np.random.rand(3, 10)
        metadata = [
            {
                "doc_id": "doc1",
                "chunk_id": "chunk1", 
                "text": "This is a substantial piece of text with good content",
                "source": {
                    "doc_type": "protocol",
                    "title": "Test Protocol"
                },
                "span": {"start": 0, "end": 50}
            },
            {
                "doc_id": "doc2",
                "chunk_id": "chunk2",
                "text": "Short text",
                "source": {"doc_type": "essay"}
            },
            {
                "doc_id": "",
                "chunk_id": "chunk3",
                "text": "Text without proper doc_id"
            }
        ]
        
        scores = builder._compute_grounding_scores(vectors, metadata)
        
        assert len(scores) == 3
        assert all(0.0 <= score <= 1.0 for score in scores)
        
        # First record should have highest score (complete metadata)
        assert scores[0] > scores[1] > scores[2]
    
    def test_compute_grounding_scores_text_quality(self):
        """Test grounding score based on text quality."""
        builder = IndexBuilder({})
        
        vectors = np.random.rand(4, 10)
        metadata = [
            {
                "doc_id": "doc1",
                "chunk_id": "chunk1",
                "text": "Very short"  # Too short
            },
            {
                "doc_id": "doc2", 
                "chunk_id": "chunk2",
                "text": "This is a medium length text that should get some points"  # Medium
            },
            {
                "doc_id": "doc3",
                "chunk_id": "chunk3", 
                "text": "This is a much longer piece of text that provides substantial content and should receive a higher grounding score because it has more meaningful information"  # Long
            },
            {
                "doc_id": "doc4",
                "chunk_id": "chunk4",
                "text": "This is an extremely long piece of text that goes on and on with lots of detailed information and comprehensive content that should definitely receive the highest grounding score because it provides the most substantial and meaningful information for retrieval purposes"  # Very long
            }
        ]
        
        scores = builder._compute_grounding_scores(vectors, metadata)
        
        # Scores should generally increase with text length (allowing for ties due to capping)
        assert scores[0] <= scores[1] <= scores[2] <= scores[3]
        
        # Very short text should get minimal score
        assert scores[0] < 0.5
        
        # Very long text should get high score
        assert scores[3] >= 0.7
        
        # At least some differentiation should exist
        assert scores[3] > scores[0]
    
    def test_compute_grounding_scores_source_quality(self):
        """Test grounding score based on source information quality."""
        builder = IndexBuilder({})
        
        vectors = np.random.rand(4, 10)
        metadata = [
            {
                "doc_id": "doc1",
                "chunk_id": "chunk1",
                "text": "This is a substantial text for testing",
                "source": {}  # Empty source
            },
            {
                "doc_id": "doc2",
                "chunk_id": "chunk2", 
                "text": "This is a substantial text for testing",
                "source": {"doc_type": "protocol"}  # Partial source
            },
            {
                "doc_id": "doc3",
                "chunk_id": "chunk3",
                "text": "This is a substantial text for testing", 
                "source": {"doc_type": "protocol", "title": "Test Title"}  # Complete source
            },
            {
                "doc_id": "doc4",
                "chunk_id": "chunk4",
                "text": "This is a substantial text for testing",
                "source": {"doc_type": "protocol", "title": "Test Title", "url": "https://example.com"}  # Extended source
            }
        ]
        
        scores = builder._compute_grounding_scores(vectors, metadata)
        
        # Scores should increase with source completeness
        assert scores[0] < scores[1] < scores[2] <= scores[3]
    
    def test_compute_grounding_scores_span_information(self):
        """Test grounding score based on span information."""
        builder = IndexBuilder({})
        
        vectors = np.random.rand(3, 10)
        metadata = [
            {
                "doc_id": "doc1",
                "chunk_id": "chunk1",
                "text": "This is a substantial text for testing"
                # No span information
            },
            {
                "doc_id": "doc2",
                "chunk_id": "chunk2",
                "text": "This is a substantial text for testing",
                "span": {"start": 0, "end": 10}  # Valid span
            },
            {
                "doc_id": "doc3",
                "chunk_id": "chunk3",
                "text": "This is a substantial text for testing",
                "span": "invalid_span"  # Invalid span format
            }
        ]
        
        scores = builder._compute_grounding_scores(vectors, metadata)
        
        # Record with valid span should score higher
        assert scores[1] > scores[0]
        assert scores[1] > scores[2]
    
    def test_compute_grounding_scores_capped_at_one(self):
        """Test that grounding scores are capped at 1.0."""
        builder = IndexBuilder({})
        
        vectors = np.random.rand(1, 10)
        metadata = [
            {
                "doc_id": "doc1",
                "chunk_id": "chunk1",
                "text": "This is an extremely comprehensive and detailed piece of text that provides substantial information",
                "source": {
                    "doc_type": "protocol",
                    "title": "Comprehensive Protocol",
                    "url": "https://example.com"
                },
                "span": {"start": 0, "end": 100}
            }
        ]
        
        scores = builder._compute_grounding_scores(vectors, metadata)
        
        # Score should be capped at 1.0
        assert scores[0] <= 1.0
        assert scores[0] > 0.9  # Should be very high
    
    def test_build_index_includes_grounding_scores(self):
        """Test that build_index includes grounding scores in metadata."""
        builder = IndexBuilder({
            "index_id": "test_index",
            "mode": "latency",
            "metadata_fields": ["doc_id", "chunk_id", "text"]
        })
        
        # Create test data
        vectors = np.random.rand(2, 10)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create vectors file
            vectors_path = Path(temp_dir) / "vectors.npy"
            np.save(vectors_path, vectors)
            
            # Create metadata file
            metadata_path = Path(temp_dir) / "metadata.jsonl"
            with open(metadata_path, 'w') as f:
                f.write(json.dumps({
                    "doc_id": "doc1",
                    "chunk_id": "chunk1",
                    "text": "This is a substantial text for testing"
                }) + '\n')
                f.write(json.dumps({
                    "doc_id": "doc2", 
                    "chunk_id": "chunk2",
                    "text": "Short text"
                }) + '\n')
            
            # Build index
            output_dir = Path(temp_dir) / "output"
            stats = builder.build_index(str(vectors_path), str(metadata_path), str(output_dir), "test_trace")
            
            # Check that metadata was saved with grounding scores
            meta_output_path = output_dir / "meta.jsonl"
            assert meta_output_path.exists()
            
            with open(meta_output_path, 'r') as f:
                lines = f.readlines()
                assert len(lines) == 2
                
                # Check first record
                record1 = json.loads(lines[0])
                assert "grounding_score" in record1
                assert 0.0 <= record1["grounding_score"] <= 1.0
                
                # Check second record
                record2 = json.loads(lines[1])
                assert "grounding_score" in record2
                assert 0.0 <= record2["grounding_score"] <= 1.0
                
                # First record should have higher score (longer text)
                assert record1["grounding_score"] > record2["grounding_score"]
