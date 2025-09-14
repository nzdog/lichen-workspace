"""
Tests for AI Room integration with RAG outputs
"""

import pytest
from unittest.mock import patch, MagicMock
from rooms.ai_room.ai_room import AIRoom, AIRoomConfig
from rooms.ai_room.types import AIRoomInput, RAGResult, AIRoomContext


class TestAIRoomIntegration:
    """Test AI Room integration with RAG outputs"""
    
    @pytest.mark.asyncio
    async def test_consent_prompt_on_first_retrieval(self):
        """Test that consent prompt is shown on first retrieval"""
        ai_room = AIRoom()
        
        # First retrieval should show consent prompt
        input_data = AIRoomInput(
            session_state_ref="test-session-1",
            brief={"task": "test query", "stones": ["test-stone"]}
        )
        
        result = await ai_room.run_ai_room(input_data)
        
        assert "consent" in result.display_text.lower() or "proceed" in result.display_text.lower()
        assert result.next_action == "continue"
        assert result.meta is None or result.meta.get("rag_processing_required") is True
    
    @pytest.mark.asyncio
    async def test_no_consent_prompt_on_subsequent_retrieval(self):
        """Test that consent prompt is not shown on subsequent retrievals"""
        ai_room = AIRoom()
        
        # First retrieval
        input_data = AIRoomInput(
            session_state_ref="test-session-2",
            brief={"task": "test query", "stones": ["test-stone"]}
        )
        
        result1 = await ai_room.run_ai_room(input_data)
        assert "consent" in result1.display_text.lower() or "proceed" in result1.display_text.lower()
        
        # Second retrieval should not show consent prompt
        result2 = await ai_room.run_ai_room(input_data)
        assert "consent" not in result2.display_text.lower()
        assert "proceed" not in result2.display_text.lower()
    
    def test_compose_response_with_rag_success(self):
        """Test composing response with successful RAG results"""
        ai_room = AIRoom()
        
        # Create mock RAG result
        rag_result = RAGResult(
            query="test query",
            lane="fast",
            retrieved_docs=[{"doc": "test_doc", "text": "test context", "score": 0.8}],
            generated_answer="This is a well-grounded answer based on our knowledge base.",
            citations=[{"source_id": "test_doc", "span": [0, 20]}],
            grounding_score=0.8,
            stones_alignment=0.7,
            hallucinations=0,
            insufficient_support=False
        )
        
        # Create context (not first retrieval)
        ctx = AIRoomContext(
            session_state_ref="test-session-3",
            brief={"task": "test query", "stones": ["test-stone"]},
            context={},
            is_first_retrieval=False
        )
        
        result = ai_room.compose_response_with_rag(rag_result, ctx)
        
        assert "well-grounded answer" in result.display_text
        assert "grounded in 1 source" in result.display_text
        # Note: stones_alignment is 0.7, which is not > 0.7, so no principles message
        assert result.next_action == "continue"
        assert result.meta["retrieval"]["lane"] == "fast"
        assert result.meta["retrieval"]["top_k"] == 1
        assert result.meta["stones_alignment"] == 0.7
        assert result.meta["grounding_score_1to5"] == 4  # 0.8 * 4 + 1 = 4.2, rounded to 4
    
    def test_compose_response_with_rag_first_retrieval(self):
        """Test composing response with RAG results on first retrieval shows consent"""
        ai_room = AIRoom()
        
        # Create mock RAG result
        rag_result = RAGResult(
            query="test query",
            lane="fast",
            retrieved_docs=[{"doc": "test_doc", "text": "test context", "score": 0.8}],
            generated_answer="This is a well-grounded answer based on our knowledge base.",
            citations=[{"source_id": "test_doc", "span": [0, 20]}],
            grounding_score=0.8,
            stones_alignment=0.7,
            hallucinations=0,
            insufficient_support=False
        )
        
        # Create context (first retrieval)
        ctx = AIRoomContext(
            session_state_ref="test-session-4",
            brief={"task": "test query", "stones": ["test-stone"]},
            context={},
            is_first_retrieval=True
        )
        
        result = ai_room.compose_response_with_rag(rag_result, ctx)
        
        assert "consent" in result.display_text.lower() or "proceed" in result.display_text.lower()
        assert result.next_action == "continue"
        assert result.meta["consent_required"] is True
    
    def test_handle_fallback_response(self):
        """Test handling fallback responses from orchestrator"""
        ai_room = AIRoom()
        
        # Test low grounding fallback
        brief = {
            "meta": {
                "fallback": "low_grounding",
                "profile": "fast",
                "grounding_score": 0.1
            }
        }
        
        result = ai_room._handle_fallback_response(brief)
        
        assert "cannot provide a confident answer" in result.display_text.lower()
        assert "insufficient grounding" in result.display_text.lower()
        assert result.next_action == "continue"
        assert result.meta["fallback"] == "low_grounding"
    
    def test_handle_no_citations_fallback(self):
        """Test handling no citations fallback responses"""
        ai_room = AIRoom()
        
        # Test no citations fallback
        brief = {
            "meta": {
                "fallback": "no_citations",
                "profile": "fast",
                "grounding_score": 0.3
            }
        }
        
        result = ai_room._handle_fallback_response(brief)
        
        assert "cannot provide a confident answer" in result.display_text.lower()
        assert "without proper citations" in result.display_text.lower()
        assert result.next_action == "continue"
        assert result.meta["fallback"] == "no_citations"
    
    def test_extract_query_from_brief(self):
        """Test extracting query from various brief formats"""
        ai_room = AIRoom()
        
        # Test dict with task
        brief1 = {"task": "test task", "stones": ["test-stone"]}
        assert ai_room._extract_query(brief1) == "test task"
        
        # Test dict with query
        brief2 = {"query": "test query", "stones": ["test-stone"]}
        assert ai_room._extract_query(brief2) == "test query"
        
        # Test string brief
        brief3 = "test string query"
        assert ai_room._extract_query(brief3) == "test string query"
        
        # Test empty brief
        brief4 = {}
        assert ai_room._extract_query(brief4) == ""
    
    def test_session_retrieval_tracking(self):
        """Test that session retrieval count is tracked correctly"""
        ai_room = AIRoom()
        
        # First retrieval should be marked as first
        assert ai_room._is_first_retrieval("session-1") is True
        assert ai_room._is_first_retrieval("session-1") is False  # Second call
        
        # Different session should be first
        assert ai_room._is_first_retrieval("session-2") is True
        assert ai_room._is_first_retrieval("session-2") is False
