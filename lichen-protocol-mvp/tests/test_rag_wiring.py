"""
Tests for RAG wiring integration with AI Room.

Tests the complete RAG pipeline in dummy mode to ensure proper integration
with the hallway orchestrator and AI Room contract.
"""

import os
import pytest
import json
from unittest.mock import Mock, patch
from pathlib import Path

# Set up dummy mode for testing
os.environ["RAG_ENABLED"] = "1"
os.environ["USE_DUMMY_RAG"] = "1"
os.environ["RAG_LANE"] = "fast"

from hallway.adapters.rag_adapter import RAGAdapter, get_rag_adapter
from hallway.orchestrator import _run_rag_retrieval
from hallway.types import ExecutionContext, Ports


class MockPorts:
    """Mock ports for testing."""
    
    def __init__(self):
        self.log = Mock()
        self.clock = Mock()
        self.clock.now_iso.return_value = "2025-01-27T10:30:45.123Z"


@pytest.fixture
def rag_adapter():
    """Create a RAG adapter instance for testing."""
    return RAGAdapter()


@pytest.fixture
def execution_context():
    """Create an execution context for testing."""
    return ExecutionContext(
        run_id="test-run-123",
        correlation_id="test-correlation-456",
        rooms_to_run=["ai_room"],
        state={
            "session_state_ref": "test-session-789",
            "payloads": {
                "ai_room": {
                    "brief": {
                        "task": "What are the key principles of effective leadership?",
                        "stones": ["Clarity Over Cleverness", "Integrity Is the Growth Strategy"]
                    },
                    "meta": {
                        "rag_lane": "fast"
                    }
                }
            }
        },
        budgets={"tokens": 1000.0, "time_ms": 5000.0},
        ports=MockPorts(),
        policy={}
    )


class TestRAGAdapter:
    """Test RAG adapter functionality."""
    
    def test_adapter_initialization(self, rag_adapter):
        """Test that RAG adapter initializes correctly."""
        assert rag_adapter.enabled
        assert rag_adapter.dummy_mode
        assert rag_adapter.default_lane == "fast"
        assert rag_adapter.config is not None
        assert rag_adapter.lanes_config is not None
    
    def test_retrieve_dummy_mode(self, rag_adapter):
        """Test retrieval in dummy mode."""
        query = "What are the key principles of effective leadership?"
        results = rag_adapter.retrieve(query, "fast")
        
        assert isinstance(results, list)
        if results:  # If dummy data is available
            assert len(results) > 0
            result = results[0]
            assert "doc" in result
            assert "chunk" in result
            assert "rank" in result
            assert "score" in result
            assert "text" in result
    
    def test_generate_dummy_mode(self, rag_adapter):
        """Test generation in dummy mode."""
        query = "What are the key principles of effective leadership?"
        context_texts = ["Effective leadership requires clarity over cleverness."]
        
        result = rag_adapter.generate(query, context_texts, "fast")
        
        assert isinstance(result, dict)
        assert "answer" in result
        assert "citations" in result
        assert "hallucinations" in result
        assert isinstance(result["citations"], list)
        assert isinstance(result["hallucinations"], int)
    
    def test_stones_align(self, rag_adapter):
        """Test Stones alignment calculation."""
        answer_text = "Effective leadership requires clarity over cleverness and integrity as the growth strategy."
        expected_stones = ["Clarity Over Cleverness", "Integrity Is the Growth Strategy"]
        
        alignment = rag_adapter.stones_align(answer_text, expected_stones)
        
        assert isinstance(alignment, float)
        assert 0.0 <= alignment <= 1.0
        assert alignment > 0.0  # Should find some alignment
    
    def test_get_lane_threshold(self, rag_adapter):
        """Test getting lane thresholds."""
        threshold = rag_adapter.get_lane_threshold("fast", "stones_alignment")
        assert isinstance(threshold, float)
        assert threshold > 0.0
    
    def test_is_sufficient_support(self, rag_adapter):
        """Test sufficient support check."""
        # Test with good alignment and no hallucinations
        sufficient = rag_adapter.is_sufficient_support("fast", 0.8, 0)
        assert sufficient
        
        # Test with poor alignment
        insufficient = rag_adapter.is_sufficient_support("fast", 0.3, 0)
        assert not insufficient
        
        # Test with hallucinations
        insufficient = rag_adapter.is_sufficient_support("fast", 0.8, 2)
        assert not insufficient


class TestRAGIntegration:
    """Test RAG integration with orchestrator."""
    
    @pytest.mark.asyncio
    async def test_rag_retrieval_integration(self, execution_context):
        """Test RAG retrieval integration with orchestrator."""
        result = await _run_rag_retrieval(execution_context)
        
        assert result is not None
        assert "meta" in result
        
        meta = result["meta"]
        assert "retrieval" in meta
        assert "stones_alignment" in meta
        assert "grounding_score_1to5" in meta
        assert "insufficient_support" in meta
        
        retrieval = meta["retrieval"]
        assert "lane" in retrieval
        assert "top_k" in retrieval
        assert "used_doc_ids" in retrieval
        assert "citations" in retrieval
    
    @pytest.mark.asyncio
    async def test_rag_retrieval_with_empty_query(self, execution_context):
        """Test RAG retrieval with empty query."""
        execution_context.state["payloads"]["ai_room"]["brief"]["task"] = ""
        
        result = await _run_rag_retrieval(execution_context)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_rag_retrieval_with_no_brief(self, execution_context):
        """Test RAG retrieval with no brief."""
        execution_context.state["payloads"]["ai_room"] = {}
        
        result = await _run_rag_retrieval(execution_context)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_rag_retrieval_error_handling(self, execution_context):
        """Test RAG retrieval error handling."""
        # Mock an error in the RAG adapter
        with patch('hallway.adapters.rag_adapter.get_rag_adapter') as mock_get_adapter:
            mock_adapter = Mock()
            mock_adapter.enabled = True
            mock_adapter.retrieve.side_effect = Exception("Test error")
            mock_get_adapter.return_value = mock_adapter
            
            result = await _run_rag_retrieval(execution_context)
            
            assert result is not None
            assert "rag_error" in result
            assert result["meta"]["insufficient_support"] is True


class TestAIRoomContract:
    """Test AI Room contract compliance."""
    
    def test_contract_schema_compliance(self):
        """Test that RAG integration maintains contract compliance."""
        # Load the AI Room contract
        contract_path = Path("contracts/rooms/ai_room.json")
        if contract_path.exists():
            with open(contract_path, 'r') as f:
                contract = json.load(f)
            
            # Check that outputs.meta exists and has required fields
            assert "outputs" in contract
            assert "meta" in contract["outputs"]
            
            meta = contract["outputs"]["meta"]
            assert "retrieval" in meta
            assert "stones_alignment" in meta
            assert "grounding_score_1to5" in meta
            assert "insufficient_support" in meta
            
            retrieval = meta["retrieval"]
            assert "lane" in retrieval
            assert "top_k" in retrieval
            assert "used_doc_ids" in retrieval
            assert "citations" in retrieval
    
    def test_optional_fields_preserved(self):
        """Test that existing optional fields are preserved."""
        contract_path = Path("contracts/rooms/ai_room.json")
        if contract_path.exists():
            with open(contract_path, 'r') as f:
                contract = json.load(f)
            
            # Check that existing fields are still present
            assert "display_text" in contract["outputs"]
            assert "next_action" in contract["outputs"]
            assert "mini_walk_supported" in contract
            assert "completion_prompt_required" in contract
            assert "diagnostics_default" in contract


class TestDummyModeIntegration:
    """Test dummy mode integration with eval harness."""
    
    def test_dummy_data_loading(self, rag_adapter):
        """Test that dummy data loads correctly."""
        if rag_adapter.dummy_mode:
            # Check that dummy data is loaded
            assert hasattr(rag_adapter, 'dummy_retrieval')
            assert hasattr(rag_adapter, 'dummy_answers')
            
            # If dummy files exist, they should be loaded
            retrieval_file = Path("../../data/dummy_retrieval.jsonl")
            answers_file = Path("../../data/dummy_answers.jsonl")
            
            if retrieval_file.exists():
                assert len(rag_adapter.dummy_retrieval) > 0
            
            if answers_file.exists():
                assert len(rag_adapter.dummy_answers) > 0
    
    def test_dummy_mode_retrieval_consistency(self, rag_adapter):
        """Test that dummy mode retrieval is consistent."""
        if not rag_adapter.dummy_mode:
            pytest.skip("Not in dummy mode")
        
        query = "What are the key principles of effective leadership?"
        
        # Multiple calls should return consistent results
        results1 = rag_adapter.retrieve(query, "fast")
        results2 = rag_adapter.retrieve(query, "fast")
        
        assert results1 == results2
    
    def test_dummy_mode_generation_consistency(self, rag_adapter):
        """Test that dummy mode generation is consistent."""
        if not rag_adapter.dummy_mode:
            pytest.skip("Not in dummy mode")
        
        query = "What are the key principles of effective leadership?"
        context_texts = ["Effective leadership requires clarity over cleverness."]
        
        # Multiple calls should return consistent results
        result1 = rag_adapter.generate(query, context_texts, "fast")
        result2 = rag_adapter.generate(query, context_texts, "fast")
        
        assert result1 == result2


if __name__ == "__main__":
    pytest.main([__file__])
