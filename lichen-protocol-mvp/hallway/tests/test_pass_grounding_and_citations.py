"""
Tests for successful RAG operations that pass both grounding and citations guardrails.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from ..orchestrator import _run_rag_retrieval
from ..types import ExecutionContext


class TestPassGroundingAndCitations:
    """Test that high grounding + citations allow RAG to proceed normally."""
    
    @pytest.mark.asyncio
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_high_grounding_with_citations_succeeds(self, mock_get_adapter):
        """Test the normal path: high grounding score + citations present."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Mock excellent retrieval results
        mock_retrieval_results = [
            {"doc": "high_quality_doc", "text": "comprehensive and relevant context", "score": 0.95},
            {"doc": "supporting_doc", "text": "additional supporting context", "score": 0.87},
            {"doc": "expert_source", "text": "authoritative information", "score": 0.82}
        ]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        # Mock excellent generation results with citations
        mock_generation_result = {
            "answer": "This is a well-grounded, comprehensive answer based on authoritative sources.",
            "citations": [  # Multiple valid citations
                {"source_id": "high_quality_doc", "span": [0, 25]},
                {"source_id": "supporting_doc", "span": [10, 35]},
                {"source_id": "expert_source", "span": [5, 30]}
            ],
            "hallucinations": 0  # No hallucinations
        }
        mock_adapter.generate.return_value = mock_generation_result
        
        # Mock high stones alignment
        mock_adapter.stones_align.return_value = 0.9
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
                            "task": "high quality test query",
                            "stones": ["excellence-stone", "truth-stone"]
                        }
                    }
                }
            }
        )
        
        # Set reasonable grounding threshold
        with patch.dict(os.environ, {'MIN_GROUNDING': '0.25'}):
            result = await _run_rag_retrieval(ctx)
        
        # Assertions - should be successful RAG result, not refusal
        assert result is not None
        
        # Should be RAG context format, not refusal format
        assert "rag_context" in result
        assert "meta" in result
        
        # Check meta information
        meta = result["meta"]
        assert meta["retrieval"]["top_k"] == 3
        assert meta["retrieval"]["citations"] == mock_generation_result["citations"]
        assert meta["stones_alignment"] == 0.9
        assert meta["grounding_score_1to5"] >= 4  # Should be high with good citations + alignment
        assert meta["insufficient_support"] == False
        
        # Check RAG context
        rag_context = result["rag_context"]
        assert rag_context["query"] == "high quality test query"
        assert rag_context["generated_answer"] == mock_generation_result["answer"]
        assert rag_context["hallucinations"] == 0
        assert len(rag_context["retrieved_docs"]) == 3
        
        # Verify both retrieval and generation were called
        mock_adapter.retrieve.assert_called_once()
        mock_adapter.generate.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('hallway.orchestrator.log_rag_turn')
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_successful_operation_logged_correctly(self, mock_get_adapter, mock_log_rag_turn):
        """Test that successful operations are logged without refusal flags."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Mock good results
        mock_retrieval_results = [
            {"doc": "quality_doc", "text": "good context", "score": 0.8}
        ]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        mock_generation_result = {
            "answer": "Good answer",
            "citations": [{"source_id": "quality_doc", "span": [0, 15]}],
            "hallucinations": 0
        }
        mock_adapter.generate.return_value = mock_generation_result
        mock_adapter.stones_align.return_value = 0.7
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
        
        # Use standard threshold
        with patch.dict(os.environ, {'MIN_GROUNDING': '0.25'}):
            result = await _run_rag_retrieval(ctx)
        
        # Verify successful logging
        mock_log_rag_turn.assert_called()
        
        # Check the call arguments - should NOT have refusal flags
        call_args = mock_log_rag_turn.call_args
        flags = call_args.kwargs['flags']
        assert flags['fallback'] is None or flags['fallback'] == None
        assert 'refusal' not in flags or flags['refusal'] is None
        assert flags['rag_enabled'] == True
        assert len(call_args.kwargs['citations']) > 0
        assert call_args.kwargs['grounding_score'] >= 0.25
    
    @pytest.mark.asyncio
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_minimal_passing_scenario(self, mock_get_adapter):
        """Test minimal scenario that still passes both guardrails."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Minimal but sufficient retrieval results
        mock_retrieval_results = [
            {"doc": "min_doc", "text": "minimal context", "score": 0.6}
        ]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        # Minimal generation results that still pass
        mock_generation_result = {
            "answer": "Minimal answer",
            "citations": [{"source_id": "min_doc", "span": [0, 10]}],  # At least one citation
            "hallucinations": 1  # Some hallucinations but not too many
        }
        mock_adapter.generate.return_value = mock_generation_result
        
        # Moderate stones alignment - enough to pass threshold
        mock_adapter.stones_align.return_value = 0.5
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
                        "brief": {"task": "minimal test", "stones": []}
                    }
                }
            }
        )
        
        # Set threshold to allow this minimal case to pass
        with patch.dict(os.environ, {'MIN_GROUNDING': '0.25'}):
            result = await _run_rag_retrieval(ctx)
        
        # Should still succeed despite being minimal
        assert result is not None
        assert "rag_context" in result
        assert "meta" in result
        
        # Grounding score should be just above threshold
        # Score = 1 (base) + 1 (citations) + 1 (stones > 0.5) = 3
        # Normalized = (3-1)/4 = 0.5, which is > 0.25 threshold
        expected_grounding_1to5 = 3  # Base + citations + stones_alignment > 0.5
        assert result["meta"]["grounding_score_1to5"] == expected_grounding_1to5
    
    @pytest.mark.asyncio
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_excellent_scenario_maximum_score(self, mock_get_adapter):
        """Test excellent scenario that achieves maximum grounding score."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Excellent retrieval results
        mock_retrieval_results = [
            {"doc": "excellent_doc", "text": "perfect context", "score": 0.99}
        ]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        # Perfect generation results
        mock_generation_result = {
            "answer": "Perfect answer with excellent grounding",
            "citations": [{"source_id": "excellent_doc", "span": [0, 20]}],
            "hallucinations": 0  # Zero hallucinations
        }
        mock_adapter.generate.return_value = mock_generation_result
        
        # Perfect stones alignment
        mock_adapter.stones_align.return_value = 0.9  # > 0.7 threshold
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
                        "brief": {"task": "excellent test", "stones": ["perfect-stone"]}
                    }
                }
            }
        )
        
        result = await _run_rag_retrieval(ctx)
        
        # Should achieve maximum grounding score
        # Score = 1 (base) + 1 (citations) + 1 (stones > 0.5) + 1 (stones > 0.7) + 1 (no hallucinations) = 5
        assert result["meta"]["grounding_score_1to5"] == 5
        assert result["meta"]["insufficient_support"] == False
        assert len(result["meta"]["retrieval"]["citations"]) > 0