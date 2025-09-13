"""
Tests for missing citations refusal guardrails.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from ..orchestrator import _run_rag_retrieval
from ..hallway_types import ExecutionContext


class TestMissingCitationsRefusal:
    """Test that missing citations trigger fallback refusal."""
    
    @pytest.mark.asyncio
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_missing_citations_triggers_refusal(self, mock_get_adapter):
        """Test that missing citations trigger refusal with correct fallback."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Mock good retrieval results
        mock_retrieval_results = [
            {"doc": "good_doc", "text": "comprehensive context", "score": 0.9},
            {"doc": "another_doc", "text": "more context", "score": 0.8}
        ]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        # Mock generation results with good content but NO CITATIONS
        mock_generation_result = {
            "answer": "This is a good answer with high quality content",
            "citations": [],  # NO CITATIONS - this should trigger refusal
            "hallucinations": 0  # Low hallucinations
        }
        mock_adapter.generate.return_value = mock_generation_result
        
        # Mock high stones alignment (good quality)
        mock_adapter.stones_align.return_value = 0.8
        mock_adapter.is_sufficient_support.return_value = True
        
        # Create execution context
        ctx = ExecutionContext(
            run_id="test-run",
            correlation_id="test-correlation",
            rooms_to_run=["ai_room"],
            budgets={},
            policy={},
            ports=MagicMock(),
            state={
                "payloads": {
                    "ai_room": {
                        "brief": {
                            "task": "test query with missing citations",
                            "stones": ["test-stone"]
                        }
                    }
                }
            }
        )
        
        # Set low grounding threshold so grounding check passes
        with patch.dict(os.environ, {'MIN_GROUNDING': '0.1'}):
            result = await _run_rag_retrieval(ctx)
        
        # Assertions - should be refused due to missing citations
        assert result is not None
        assert result["text"] == "Cannot answer confidently: insufficient grounding."
        assert result["citations"] == []
        assert result["meta"]["fallback"] == "no_citations"
        assert result["meta"]["profile"] in ["fast", "accurate"]
        assert "grounding_score" in result["meta"]
        
        # Verify that both retrieval and generation were called
        mock_adapter.retrieve.assert_called_once()
        mock_adapter.generate.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_empty_citations_array_triggers_refusal(self, mock_get_adapter):
        """Test that explicitly empty citations array triggers refusal."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Mock retrieval results
        mock_retrieval_results = [
            {"doc": "test_doc", "text": "test context", "score": 0.7}
        ]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        # Mock generation with explicit empty citations
        mock_generation_result = {
            "answer": "Good quality answer",
            "citations": [],  # Explicitly empty
            "hallucinations": 0
        }
        mock_adapter.generate.return_value = mock_generation_result
        mock_adapter.stones_align.return_value = 0.7
        
        # Create execution context
        ctx = ExecutionContext(
            run_id="test-run",
            correlation_id="test-correlation",
            rooms_to_run=["ai_room"],
            budgets={},
            policy={},
            ports=MagicMock(),
            state={
                "payloads": {
                    "ai_room": {
                        "brief": {"task": "test query", "stones": []}
                    }
                }
            }
        )
        
        result = await _run_rag_retrieval(ctx)
        
        # Should trigger no_citations refusal
        assert result["meta"]["fallback"] == "no_citations"
        assert result["citations"] == []
    
    @pytest.mark.asyncio
    @patch('hallway.orchestrator.log_rag_turn')
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_missing_citations_logged_correctly(self, mock_get_adapter, mock_log_rag_turn):
        """Test that missing citations refusal events are logged correctly."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Good retrieval but no citations in generation
        mock_retrieval_results = [{"doc": "doc1", "text": "context", "score": 0.8}]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        mock_generation_result = {
            "answer": "Answer without citations",
            "citations": [],  # Missing citations
            "hallucinations": 0
        }
        mock_adapter.generate.return_value = mock_generation_result
        mock_adapter.stones_align.return_value = 0.6
        
        # Create execution context
        ctx = ExecutionContext(
            run_id="test-run",
            correlation_id="test-correlation",
            rooms_to_run=["ai_room"],
            budgets={},
            policy={},
            ports=MagicMock(),
            state={
                "payloads": {
                    "ai_room": {
                        "brief": {"task": "test query", "stones": []}
                    }
                }
            }
        )
        
        # Use low grounding threshold so only citations check fails
        with patch.dict(os.environ, {'MIN_GROUNDING': '0.1'}):
            result = await _run_rag_retrieval(ctx)
        
        # Verify logging was called with no_citations flags
        mock_log_rag_turn.assert_called()
        
        # Check the call arguments
        call_args = mock_log_rag_turn.call_args
        assert call_args.kwargs['flags']['fallback'] == 'no_citations'
        assert call_args.kwargs['flags']['refusal'] == 'no_citations'
        assert call_args.kwargs['citations'] == []
    
    @pytest.mark.asyncio
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_valid_citations_pass_guardrail(self, mock_get_adapter):
        """Test that valid citations allow the request to proceed."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Mock good retrieval results
        mock_retrieval_results = [
            {"doc": "good_doc", "text": "comprehensive context", "score": 0.9}
        ]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        # Mock generation with VALID CITATIONS
        mock_generation_result = {
            "answer": "Well-supported answer",
            "citations": [  # Valid citations present
                {"source_id": "good_doc", "span": [0, 20]},
                {"source_id": "good_doc", "span": [30, 50]}
            ],
            "hallucinations": 0
        }
        mock_adapter.generate.return_value = mock_generation_result
        mock_adapter.stones_align.return_value = 0.8
        mock_adapter.is_sufficient_support.return_value = True
        
        # Create execution context
        ctx = ExecutionContext(
            run_id="test-run",
            correlation_id="test-correlation",
            rooms_to_run=["ai_room"],
            budgets={},
            policy={},
            ports=MagicMock(),
            state={
                "payloads": {
                    "ai_room": {
                        "brief": {"task": "test query", "stones": ["test-stone"]}
                    }
                }
            }
        )
        
        # Set low grounding threshold so both checks pass
        with patch.dict(os.environ, {'MIN_GROUNDING': '0.1'}):
            result = await _run_rag_retrieval(ctx)
        
        # Should NOT trigger refusal - should return successful RAG result
        assert result is not None
        assert "text" not in result  # This is the RAG context format, not refusal format
        assert "meta" in result
        assert result["meta"]["retrieval"]["citations"] == mock_generation_result["citations"]
        assert "fallback" not in result["meta"] or result["meta"].get("fallback") is None