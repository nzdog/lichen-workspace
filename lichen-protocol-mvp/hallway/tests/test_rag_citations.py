"""
Tests for RAG citations functionality.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from ..rag_observability import RAGObservability, log_rag_turn


class TestRAGCitations:
    """Test RAG citations extraction and logging."""
    
    def test_extract_citations_from_results_with_spans(self):
        """Test citation extraction when results have spans."""
        obs = RAGObservability()
        
        results = [
            {
                "doc_id": "doc1",
                "chunk_id": "chunk1",
                "text": "This is some text",
                "spans": [
                    {"start": 0, "end": 4},
                    {"start": 10, "end": 14}
                ]
            },
            {
                "doc_id": "doc2", 
                "chunk_id": "chunk2",
                "text": "More text here",
                "spans": [
                    {"start": 5, "end": 9}
                ]
            }
        ]
        
        citations = obs._extract_citations_from_results(results)
        
        assert len(citations) == 3
        assert citations[0] == {"source_id": "doc1", "span_start": 0, "span_end": 4}
        assert citations[1] == {"source_id": "doc1", "span_start": 10, "span_end": 14}
        assert citations[2] == {"source_id": "doc2", "span_start": 5, "span_end": 9}
    
    def test_extract_citations_from_results_without_spans(self):
        """Test citation extraction when results don't have spans."""
        obs = RAGObservability()
        
        results = [
            {
                "doc_id": "doc1",
                "chunk_id": "chunk1",
                "text": "This is some text"
            },
            {
                "doc_id": "doc2",
                "chunk_id": "chunk2", 
                "text": "More text here"
            }
        ]
        
        citations = obs._extract_citations_from_results(results)
        
        assert len(citations) == 2
        assert citations[0] == {"source_id": "doc1", "span_start": 0, "span_end": 17}
        assert citations[1] == {"source_id": "doc2", "span_start": 0, "span_end": 14}
    
    def test_extract_citations_skips_empty_doc_id(self):
        """Test citation extraction skips results with empty doc_id."""
        obs = RAGObservability()
        
        results = [
            {
                "doc_id": "doc1",
                "text": "Valid text"
            },
            {
                "doc_id": "",
                "text": "Invalid text"
            },
            {
                "text": "No doc_id"
            }
        ]
        
        citations = obs._extract_citations_from_results(results)
        
        assert len(citations) == 1
        assert citations[0]["source_id"] == "doc1"
    
    def test_log_rag_turn_includes_citations(self):
        """Test that log_rag_turn includes citations in the event."""
        obs = RAGObservability()
        obs.enabled = True  # Enable for testing
        
        results = [
            {
                "doc_id": "doc1",
                "text": "Test text",
                "spans": [{"start": 0, "end": 4}]
            }
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            obs.obs_dir = temp_dir
            
            obs.log_rag_turn(
                turn_id="test_turn",
                lane="fast",
                query="test query",
                retrieval_metrics={"elapsed_ms": 100},
                results=results,
                generation_metrics={"elapsed_ms": 200}
            )
            
            # Check that log file was created
            log_files = list(Path(temp_dir).glob("*.jsonl"))
            assert len(log_files) == 1
            
            # Read and parse the log entry
            with open(log_files[0], 'r') as f:
                log_entry = json.loads(f.read().strip())
            
            assert "citations" in log_entry
            assert len(log_entry["citations"]) == 1
            assert log_entry["citations"][0] == {"source_id": "doc1", "span_start": 0, "span_end": 4}
    
    def test_log_rag_turn_with_provided_citations(self):
        """Test that log_rag_turn uses provided citations instead of extracting."""
        obs = RAGObservability()
        obs.enabled = True
        
        results = [
            {
                "doc_id": "doc1",
                "text": "Test text"
            }
        ]
        
        provided_citations = [
            {"source_id": "custom_doc", "span_start": 10, "span_end": 20}
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            obs.obs_dir = temp_dir
            
            obs.log_rag_turn(
                turn_id="test_turn",
                lane="fast", 
                query="test query",
                retrieval_metrics={"elapsed_ms": 100},
                results=results,
                generation_metrics={"elapsed_ms": 200},
                citations=provided_citations
            )
            
            # Check that provided citations were used
            log_files = list(Path(temp_dir).glob("*.jsonl"))
            with open(log_files[0], 'r') as f:
                log_entry = json.loads(f.read().strip())
            
            assert log_entry["citations"] == provided_citations
    
    def test_global_log_rag_turn_function(self):
        """Test the global log_rag_turn function includes citations."""
        with patch('hallway.rag_observability._rag_obs') as mock_obs:
            mock_obs.enabled = True
            
            results = [
                {
                    "doc_id": "doc1",
                    "text": "Test text",
                    "spans": [{"start": 0, "end": 4}]
                }
            ]
            
            log_rag_turn(
                turn_id="test_turn",
                lane="fast",
                query="test query", 
                retrieval_metrics={"elapsed_ms": 100},
                results=results,
                generation_metrics={"elapsed_ms": 200}
            )
            
            # Verify the mock was called with citations parameter
            mock_obs.log_rag_turn.assert_called_once()
            call_args = mock_obs.log_rag_turn.call_args
            assert len(call_args[0]) == 8  # positional args (including citations)
            assert call_args[0][7] is None  # citations should be None (will be extracted)


class TestRAGCitationsIntegration:
    """Test RAG citations integration with other components."""
    
    def test_citations_required_for_claimful_answers(self):
        """Test that claimful answers must have citations."""
        obs = RAGObservability()
        
        # Test case: answer with claims but no citations
        results_without_citations = [
            {
                "doc_id": "",
                "text": "Some text without proper source"
            }
        ]
        
        citations = obs._extract_citations_from_results(results_without_citations)
        assert len(citations) == 0
        
        # Test case: answer with claims and proper citations
        results_with_citations = [
            {
                "doc_id": "protocol_123",
                "text": "This is a well-sourced claim",
                "spans": [{"start": 0, "end": 10}]
            }
        ]
        
        citations = obs._extract_citations_from_results(results_with_citations)
        assert len(citations) == 1
        assert citations[0]["source_id"] == "protocol_123"
    
    def test_citation_format_validation(self):
        """Test that citations have the required format."""
        obs = RAGObservability()
        
        results = [
            {
                "doc_id": "doc1",
                "text": "Test text",
                "spans": [{"start": 5, "end": 10}]
            }
        ]
        
        citations = obs._extract_citations_from_results(results)
        
        assert len(citations) == 1
        citation = citations[0]
        
        # Check required fields
        assert "source_id" in citation
        assert "span_start" in citation
        assert "span_end" in citation
        
        # Check field types and values
        assert isinstance(citation["source_id"], str)
        assert isinstance(citation["span_start"], int)
        assert isinstance(citation["span_end"], int)
        assert citation["span_start"] >= 0
        assert citation["span_end"] > citation["span_start"]
