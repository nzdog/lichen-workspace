"""
Tests for RAG lane escalation policy.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from ..orchestrator import _run_rag_retrieval, _should_escalate_to_accurate, _calculate_query_complexity
from ..hallway_types import ExecutionContext


class TestEscalationPolicy:
    """Test the lane escalation policy implementation."""
    
    @pytest.mark.asyncio
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_low_grounding_escalates_to_accurate(self, mock_get_adapter):
        """Test that low grounding score escalates from fast to accurate."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Mock fast lane results with low grounding
        mock_retrieval_results = [
            {"doc": "test_doc", "text": "minimal context", "score": 0.3}
        ]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        # Mock generation with poor results (no citations, high hallucinations)
        mock_generation_result = {
            "answer": "Low confidence answer",
            "citations": [],  # No citations
            "hallucinations": 1
        }
        mock_adapter.generate.return_value = mock_generation_result
        mock_adapter.stones_align.return_value = 0.2  # Low alignment
        
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
        
        # Set escalation threshold to trigger escalation
        with patch.dict(os.environ, {
            'RAG_GROUNDING_THRESHOLD': '0.65',
            'RAG_DISABLE_ESCALATION': '0'
        }):
            result = await _run_rag_retrieval(ctx)
        
        # Should have escalated to accurate lane
        # Verify that retrieve was called twice (fast then accurate)
        assert mock_adapter.retrieve.call_count == 2
        
        # First call should be with fast lane
        first_call_args = mock_adapter.retrieve.call_args_list[0]
        assert first_call_args[0][1] == "fast"  # lane parameter
        
        # Second call should be with accurate lane
        second_call_args = mock_adapter.retrieve.call_args_list[1]
        assert second_call_args[0][1] == "accurate"  # lane parameter
    
    @pytest.mark.asyncio
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_no_citations_escalates_to_accurate(self, mock_get_adapter):
        """Test that missing citations escalates from fast to accurate."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Mock fast lane results
        mock_retrieval_results = [
            {"doc": "test_doc", "text": "good context", "score": 0.8}
        ]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        # Mock generation with good grounding but no citations
        mock_generation_result = {
            "answer": "Good answer but no citations",
            "citations": [],  # No citations - should trigger escalation
            "hallucinations": 0
        }
        mock_adapter.generate.return_value = mock_generation_result
        mock_adapter.stones_align.return_value = 0.8  # Good alignment
        
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
                            "task": "test query without citations",
                            "stones": ["test-stone"]
                        }
                    }
                }
            }
        )
        
        # Set grounding threshold high so only citations trigger escalation
        with patch.dict(os.environ, {
            'RAG_GROUNDING_THRESHOLD': '0.3',  # Low threshold
            'RAG_DISABLE_ESCALATION': '0'
        }):
            result = await _run_rag_retrieval(ctx)
        
        # Should have escalated to accurate lane due to no citations
        assert mock_adapter.retrieve.call_count == 2
        
        # First call should be with fast lane
        first_call_args = mock_adapter.retrieve.call_args_list[0]
        assert first_call_args[0][1] == "fast"
        
        # Second call should be with accurate lane
        second_call_args = mock_adapter.retrieve.call_args_list[1]
        assert second_call_args[0][1] == "accurate"
    
    @pytest.mark.asyncio
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_high_complexity_escalates_to_accurate(self, mock_get_adapter):
        """Test that high complexity queries escalate from fast to accurate."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Mock fast lane results
        mock_retrieval_results = [
            {"doc": "test_doc", "text": "context", "score": 0.7}
        ]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        # Mock generation with good results
        mock_generation_result = {
            "answer": "Good answer with citations",
            "citations": [{"source_id": "test_doc", "span": [0, 10]}],
            "hallucinations": 0
        }
        mock_adapter.generate.return_value = mock_generation_result
        mock_adapter.stones_align.return_value = 0.8
        
        # Create execution context with complex query
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
                            "task": "Compare and evaluate the pros and cons of different approaches to solve this complex problem step by step",
                            "stones": ["test-stone"]
                        }
                    }
                }
            }
        )
        
        # Set complexity threshold to trigger escalation
        with patch.dict(os.environ, {
            'RAG_GROUNDING_THRESHOLD': '0.3',  # Low threshold
            'RAG_COMPLEXITY_THRESHOLD': '0.5',  # Should trigger for complex query
            'RAG_DISABLE_ESCALATION': '0'
        }):
            result = await _run_rag_retrieval(ctx)
        
        # Should have escalated to accurate lane due to high complexity
        assert mock_adapter.retrieve.call_count == 2
        
        # First call should be with fast lane
        first_call_args = mock_adapter.retrieve.call_args_list[0]
        assert first_call_args[0][1] == "fast"
        
        # Second call should be with accurate lane
        second_call_args = mock_adapter.retrieve.call_args_list[1]
        assert second_call_args[0][1] == "accurate"
    
    @pytest.mark.asyncio
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_high_risk_intent_escalates_to_accurate(self, mock_get_adapter):
        """Test that high-risk user intent escalates from fast to accurate."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Mock fast lane results
        mock_retrieval_results = [
            {"doc": "test_doc", "text": "context", "score": 0.7}
        ]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        # Mock generation with good results
        mock_generation_result = {
            "answer": "Good answer with citations",
            "citations": [{"source_id": "test_doc", "span": [0, 10]}],
            "hallucinations": 0
        }
        mock_adapter.generate.return_value = mock_generation_result
        mock_adapter.stones_align.return_value = 0.8
        
        # Create execution context with high-risk intent
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
                            "task": "simple query",
                            "stones": ["test-stone"]
                        },
                        "meta": {
                            "user_intent": "decision"  # High-risk intent
                        }
                    }
                }
            }
        )
        
        # Set thresholds to not trigger other escalation reasons
        with patch.dict(os.environ, {
            'RAG_GROUNDING_THRESHOLD': '0.3',  # Low threshold
            'RAG_COMPLEXITY_THRESHOLD': '0.9',  # High threshold
            'RAG_DISABLE_ESCALATION': '0'
        }):
            result = await _run_rag_retrieval(ctx)
        
        # Should have escalated to accurate lane due to high-risk intent
        assert mock_adapter.retrieve.call_count == 2
        
        # First call should be with fast lane
        first_call_args = mock_adapter.retrieve.call_args_list[0]
        assert first_call_args[0][1] == "fast"
        
        # Second call should be with accurate lane
        second_call_args = mock_adapter.retrieve.call_args_list[1]
        assert second_call_args[0][1] == "accurate"
    
    @pytest.mark.asyncio
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_disabled_escalation_stays_in_fast(self, mock_get_adapter):
        """Test that disabled escalation stays in fast lane even with low grounding."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Mock fast lane results with low grounding
        mock_retrieval_results = [
            {"doc": "test_doc", "text": "minimal context", "score": 0.1}
        ]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        # Mock generation with poor results
        mock_generation_result = {
            "answer": "Low confidence answer",
            "citations": [],
            "hallucinations": 1
        }
        mock_adapter.generate.return_value = mock_generation_result
        mock_adapter.stones_align.return_value = 0.1
        
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
        
        # Disable escalation
        with patch.dict(os.environ, {
            'RAG_GROUNDING_THRESHOLD': '0.65',
            'RAG_DISABLE_ESCALATION': '1'  # Disable escalation
        }):
            result = await _run_rag_retrieval(ctx)
        
        # Should NOT have escalated - only one retrieve call
        assert mock_adapter.retrieve.call_count == 1
        
        # Should be called with fast lane only
        call_args = mock_adapter.retrieve.call_args
        assert call_args[0][1] == "fast"
    
    @pytest.mark.asyncio
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_forced_lane_bypasses_policy(self, mock_get_adapter):
        """Test that forced lane bypasses escalation policy."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Mock results
        mock_retrieval_results = [
            {"doc": "test_doc", "text": "context", "score": 0.7}
        ]
        mock_adapter.retrieve.return_value = mock_retrieval_results
        
        mock_generation_result = {
            "answer": "Good answer",
            "citations": [{"source_id": "test_doc", "span": [0, 10]}],
            "hallucinations": 0
        }
        mock_adapter.generate.return_value = mock_generation_result
        mock_adapter.stones_align.return_value = 0.8
        
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
        
        # Force accurate lane
        with patch.dict(os.environ, {
            'RAG_FORCE_LANE': 'accurate'
        }):
            result = await _run_rag_retrieval(ctx)
        
        # Should use forced lane without escalation logic
        assert mock_adapter.retrieve.call_count == 1
        
        # Should be called with forced accurate lane
        call_args = mock_adapter.retrieve.call_args
        assert call_args[0][1] == "accurate"
    
    def test_should_escalate_to_accurate_function(self):
        """Test the escalation decision function directly."""
        # Test low grounding
        should_escalate, reason = _should_escalate_to_accurate(
            "test query", [], 0.5, None
        )
        assert should_escalate == True
        assert reason == "low_grounding"
        
        # Test no citations
        should_escalate, reason = _should_escalate_to_accurate(
            "test query", [], 0.8, None
        )
        assert should_escalate == True
        assert reason == "no_citations"
        
        # Test high complexity - use a more complex query with lower threshold
        with patch.dict(os.environ, {'RAG_COMPLEXITY_THRESHOLD': '0.5'}):
            should_escalate, reason = _should_escalate_to_accurate(
                "Compare and evaluate the pros and cons of different approaches step by step and analyze the similarities and differences", 
                [{"source_id": "doc1", "span": [0, 10]}], 0.8, None
            )
            assert should_escalate == True
            assert reason == "high_complexity"
        
        # Test high-risk intent
        should_escalate, reason = _should_escalate_to_accurate(
            "simple query", 
            [{"source_id": "doc1", "span": [0, 10]}], 0.8, "decision"
        )
        assert should_escalate == True
        assert reason == "high_risk_intent"
        
        # Test no escalation needed
        should_escalate, reason = _should_escalate_to_accurate(
            "simple query", 
            [{"source_id": "doc1", "span": [0, 10]}], 0.8, None
        )
        assert should_escalate == False
        assert reason == ""
    
    def test_calculate_query_complexity(self):
        """Test query complexity calculation."""
        # Simple query
        complexity = _calculate_query_complexity("simple query")
        assert complexity < 0.5
        
        # Complex query with patterns
        complexity = _calculate_query_complexity("Compare and evaluate the pros and cons step by step")
        assert complexity > 0.5
        
        # Long query
        long_query = " ".join(["word"] * 60)  # 60 words
        complexity = _calculate_query_complexity(long_query)
        assert complexity > 0.5
        
        # Empty query
        complexity = _calculate_query_complexity("")
        assert complexity == 0.0
