"""
Smoke tests for retrieval functionality.

Tests that the retrieval system returns sensible results for known queries.
"""

import pytest
import os
import sys
from pathlib import Path

# Add the lichen-protocol-mvp directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "lichen-protocol-mvp"))

from hallway.adapters.rag_adapter import RAGAdapter


class TestRetrievalSmoke:
    """Smoke tests for retrieval functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Unset any environment variables that might interfere
        for env_var in ["RAG_EMBEDDING_MODEL", "RAG_ACCURATE_EMBEDDING_MODEL", "RAG_FAST_EMBEDDING_MODEL"]:
            if env_var in os.environ:
                del os.environ[env_var]
        
        # Set tokenizers parallelism to false
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        # Initialize RAG adapter
        self.rag_adapter = RAGAdapter()
    
    def test_fast_lane_retrieval(self):
        """Test that fast lane retrieval returns results."""
        # Test with a query that should match some content
        query = "pace gate"
        results = self.rag_adapter.retrieve(query, "fast")
        
        # Assertions
        assert len(results) >= 1, f"Fast lane should return at least 1 result, got {len(results)}"
        
        # Check that results have required fields
        for result in results:
            assert "text" in result, "Result should have 'text' field"
            assert "score" in result, "Result should have 'score' field"
            assert "doc" in result, "Result should have 'doc' field"
            assert len(result["text"]) > 0, "Result text should not be empty"
            assert isinstance(result["score"], (int, float)), "Score should be numeric"
            # Cross-encoder scores can be negative (logits), so just check they're numeric
    
    def test_accurate_lane_retrieval(self):
        """Test that accurate lane retrieval returns results."""
        # Test with a query that should match some content
        query = "mirror"
        results = self.rag_adapter.retrieve(query, "accurate")
        
        # Assertions
        assert len(results) >= 1, f"Accurate lane should return at least 1 result, got {len(results)}"
        
        # Check that results have required fields
        for result in results:
            assert "text" in result, "Result should have 'text' field"
            assert "score" in result, "Result should have 'score' field"
            assert "doc" in result, "Result should have 'doc' field"
            assert len(result["text"]) > 0, "Result text should not be empty"
            assert isinstance(result["score"], (int, float)), "Score should be numeric"
            # Cross-encoder scores can be negative (logits), so just check they're numeric
    
    def test_accurate_lane_reranking(self):
        """Test that accurate lane reranking preserves or improves score order."""
        query = "leadership"
        results = self.rag_adapter.retrieve(query, "accurate")
        
        # Should have results
        assert len(results) >= 1, f"Accurate lane should return at least 1 result, got {len(results)}"
        
        # Check that scores are in descending order (best first)
        scores = [result["score"] for result in results]
        assert scores == sorted(scores, reverse=True), "Results should be sorted by score descending"
        
        # Check that the best score is reasonable
        best_score = scores[0]
        # Cross-encoder scores can be negative (logits), so just check they're numeric
        assert isinstance(best_score, (int, float)), "Best score should be numeric"
        
        # If we have multiple results, check that reranking preserved quality
        if len(results) > 1:
            # The top result should have a score >= median of all scores
            median_score = sorted(scores)[len(scores) // 2]
            assert best_score >= median_score, f"Best score {best_score} should be >= median {median_score}"
    
    def test_empty_query_handling(self):
        """Test that empty queries are handled gracefully."""
        # Test with empty query
        results = self.rag_adapter.retrieve("", "fast")
        # Should either return empty results or handle gracefully
        assert isinstance(results, list), "Results should be a list"
        
        # Test with very short query
        results = self.rag_adapter.retrieve("a", "fast")
        assert isinstance(results, list), "Results should be a list"
    
    def test_model_consistency(self):
        """Test that both lanes use consistent embedding models."""
        # Get model info for both lanes
        fast_embed_model, _ = self.rag_adapter.get_active_model_ids("fast")
        accurate_embed_model, _ = self.rag_adapter.get_active_model_ids("accurate")
        
        # Both should use the same embedding model (all-MiniLM-L6-v2)
        assert fast_embed_model == accurate_embed_model, f"Both lanes should use same embedding model: fast={fast_embed_model}, accurate={accurate_embed_model}"
        assert "all-MiniLM-L6-v2" in fast_embed_model, f"Fast lane should use all-MiniLM-L6-v2, got {fast_embed_model}"
        assert "all-MiniLM-L6-v2" in accurate_embed_model, f"Accurate lane should use all-MiniLM-L6-v2, got {accurate_embed_model}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
