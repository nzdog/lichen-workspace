"""
Tests for RAG observability wiring.
"""

import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hallway.adapters.rag_adapter import get_rag_adapter


def test_rag_observability_basic():
    """Test that RAG observability logging works with enabled flag."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set environment variables for testing
        env_vars = {
            "RAG_ENABLED": "1",
            "RAG_OBS_ENABLED": "1",
            "RAG_OBS_DIR": temp_dir,
            "RAG_OBS_SAMPLING": "1.0",
            "USE_DUMMY_RAG": "1"  # Use dummy mode for predictable testing
        }
        
        with patch.dict(os.environ, env_vars):
            # Clear any cached adapter instance
            from hallway.adapters import rag_adapter
            rag_adapter._rag_adapter = None
            
            # Test that logging system can be imported
            from hallway.rag_observability import log_rag_turn
            
            # Create a sample log event
            log_rag_turn(
                turn_id="test-turn-123",
                lane="fast",
                query="test query",
                retrieval_metrics={
                    "elapsed_ms": 100.5,
                    "topk": 5,
                    "breadth": 10,
                    "embed_model": "test-model",
                    "index": {"path": "test.faiss", "dim": 384, "count": 1000},
                    "reranker_model": None,
                    "rerank_elapsed_ms": None
                },
                results=[
                    {"rank": 1, "doc": "doc1", "chunk": 0, "score": 0.95},
                    {"rank": 2, "doc": "doc2", "chunk": 1, "score": 0.87}
                ],
                generation_metrics={
                    "elapsed_ms": 50.0,
                    "grounding": 4.0,
                    "stones_alignment": 0.8,
                    "hallucination": 0.0
                }
            )
            
            # Check that log file was created
            log_files = list(Path(temp_dir).glob("*.jsonl"))
            assert len(log_files) > 0, "Log file should be created"
            
            # Check content
            with open(log_files[0]) as f:
                lines = f.readlines()
                assert len(lines) > 0, "Log file should have events"
                
                event = json.loads(lines[-1])
                assert event["turn_id"] == "test-turn-123"
                assert event["lane"] == "fast"


def test_rag_observability_disabled():
    """Test that no logging occurs when observability is disabled."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        env_vars = {
            "RAG_ENABLED": "1", 
            "RAG_OBS_ENABLED": "0",  # Disabled
            "RAG_OBS_DIR": temp_dir,
            "USE_DUMMY_RAG": "1"
        }
        
        with patch.dict(os.environ, env_vars):
            from hallway.rag_observability import log_rag_turn
            
            # Try to log - should be no-op
            log_rag_turn("test", "fast", "query", {}, [], {})
            
            # Check that no log files were created
            log_files = list(Path(temp_dir).glob("*.jsonl"))
            assert len(log_files) == 0, "No log files when observability disabled"


def test_rag_observability_sampling():
    """Test that sampling rate is respected."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        env_vars = {
            "RAG_ENABLED": "1",
            "RAG_OBS_ENABLED": "1", 
            "RAG_OBS_DIR": temp_dir,
            "RAG_OBS_SAMPLING": "0.0",  # No sampling
            "USE_DUMMY_RAG": "1"
        }
        
        with patch.dict(os.environ, env_vars):
            from hallway.rag_observability import log_rag_turn
            
            # Try to log - should be no-op due to sampling
            for i in range(5):
                log_rag_turn(f"test-{i}", "fast", "query", {}, [], {})
            
            # Check that no events were logged due to zero sampling
            log_files = list(Path(temp_dir).glob("*.jsonl"))
            total_lines = 0
            for log_file in log_files:
                with open(log_file) as f:
                    total_lines += len(f.readlines())
            
            assert total_lines == 0, "No events with 0.0 sampling rate"


if __name__ == "__main__":
    # Run tests directly
    test_rag_observability_basic()
    test_rag_observability_disabled() 
    test_rag_observability_sampling()
    print("All tests passed!")