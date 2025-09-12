"""
Tests for low grounding refusal guardrails.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from ..orchestrator import _run_rag_retrieval
from ..types import ExecutionContext


class TestLowGroundingRefusal:
    """Test that low grounding scores trigger fallback refusal."""
    
    @pytest.mark.asyncio
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_low_grounding_triggers_refusal(self, mock_get_adapter):
        """Test that low grounding score triggers refusal with correct fallback."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Mock retrieval results that will lead to low grounding
        mock_retrieval_results = [
            {"doc": "test_doc", "text": "minimal context", "score": 0.1}
        ]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        # Mock generation results with no citations and high hallucinations
        mock_generation_result = {
            "answer": "This is a low-confidence answer",
            "citations": [],  # No citations
            "hallucinations": 1  # High hallucinations
        }
        mock_adapter.generate.return_value = mock_generation_result
        
        # Mock stones alignment to be very low
        mock_adapter.stones_align.return_value = 0.1
        mock_adapter.is_sufficient_support.return_value = False
        
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
                            "task": "test query with low grounding",
                            "stones": ["test-stone"]
                        }
                    }
                }
            }
        )
        
        # Set minimum grounding threshold high to trigger refusal
        with patch.dict(os.environ, {'MIN_GROUNDING': '0.5'}):
            result = await _run_rag_retrieval(ctx)
        
        # Assertions
        assert result is not None
        assert result["text"] == "Cannot answer confidently: insufficient grounding."
        assert result["citations"] == []
        assert result["meta"]["fallback"] == "low_grounding"
        assert result["meta"]["profile"] in ["fast", "accurate"]
        assert "grounding_score" in result["meta"]
        assert result["meta"]["grounding_score"] < 0.5
        
        # Verify that generation was attempted but result was rejected
        mock_adapter.retrieve.assert_called_once()
        mock_adapter.generate.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_no_retrieval_results_triggers_refusal(self, mock_get_adapter):
        """Test that empty retrieval results are handled gracefully."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Mock empty retrieval results
        mock_adapter.retrieve.return_value = []
        
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
                            "task": "test query with no results",
                            "stones": []
                        }
                    }
                }
            }
        )
        
        result = await _run_rag_retrieval(ctx)
        
        # Should return empty results, not trigger grounding check
        assert result is not None
        assert "meta" in result
        assert result["meta"]["retrieval"]["top_k"] == 0
        
        # Generation should not be called with empty results
        mock_adapter.generate.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('hallway.orchestrator.log_rag_turn')
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_refusal_logged_correctly(self, mock_get_adapter, mock_log_rag_turn):
        """Test that refusal events are logged with correct flags."""
        # Mock the RAG adapter for low grounding scenario
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        mock_retrieval_results = [
            {"doc": "test_doc", "text": "minimal context", "score": 0.1}
        ]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        # Mock generation with poor results
        mock_generation_result = {
            "answer": "Poor answer",
            "citations": [],
            "hallucinations": 1
        }
        mock_adapter.generate.return_value = mock_generation_result
        mock_adapter.stones_align.return_value = 0.05
        
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
                            "task": "test query",
                            "stones": ["test-stone"]
                        }
                    }
                }
            }
        )
        
        # Trigger refusal with high threshold
        with patch.dict(os.environ, {'MIN_GROUNDING': '0.5'}):
            result = await _run_rag_retrieval(ctx)
        
        # Verify logging was called with refusal flags
        mock_log_rag_turn.assert_called()
        
        # Check the call arguments
        call_args = mock_log_rag_turn.call_args
        assert call_args.kwargs['flags']['fallback'] == 'low_grounding'
        assert call_args.kwargs['flags']['refusal'] == 'low_grounding'
        assert call_args.kwargs['citations'] == []
        assert call_args.kwargs['grounding_score'] < 0.5