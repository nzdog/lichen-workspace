"""
Unit tests for RAG adapter model configuration integration.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from ..rag_adapter import RAGAdapter
from ..model_config import ModelConfig


class TestRAGAdapterModelConfig:
    """Test cases for RAG adapter model configuration integration."""
    
    def test_rag_adapter_initializes_model_config(self):
        """Test that RAG adapter initializes model configuration."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            adapter = RAGAdapter()
            assert hasattr(adapter, 'model_config')
            assert isinstance(adapter.model_config, ModelConfig)
    
    def test_get_active_model_ids(self):
        """Test get_active_model_ids method."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            adapter = RAGAdapter()
            
            # Test fast lane
            embed, reranker = adapter.get_active_model_ids("fast")
            assert embed == "sentence-transformers/all-MiniLM-L6-v2"
            assert reranker is None
            
            # Test accurate lane
            embed, reranker = adapter.get_active_model_ids("accurate")
            assert embed == "sentence-transformers/all-mpnet-base-v2"
            assert reranker == "cross-encoder/ms-marco-electra-base"
    
    def test_get_all_active_model_ids(self):
        """Test get_all_active_model_ids method."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            adapter = RAGAdapter()
            all_ids = adapter.get_all_active_model_ids()
            
            assert "fast" in all_ids
            assert "accurate" in all_ids
            assert all_ids["fast"]["embed_model"] == "sentence-transformers/all-MiniLM-L6-v2"
            assert all_ids["fast"]["reranker_model"] is None
            assert all_ids["accurate"]["embed_model"] == "sentence-transformers/all-mpnet-base-v2"
            assert all_ids["accurate"]["reranker_model"] == "cross-encoder/ms-marco-electra-base"
    
    def test_environment_variable_override_integration(self):
        """Test that environment variables work through the adapter."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            with patch.dict(os.environ, {
                'RAG_FAST_EMBED': 'sentence-transformers/all-MiniLM-L12-v2',
                'RAG_ACCURATE_RERANK': 'cross-encoder/ms-marco-MiniLM-L-6-v2'
            }):
                adapter = RAGAdapter()
                
                # Test fast lane with embed override
                embed, reranker = adapter.get_active_model_ids("fast")
                assert embed == "sentence-transformers/all-MiniLM-L12-v2"
                assert reranker is None
                
                # Test accurate lane with reranker override
                embed, reranker = adapter.get_active_model_ids("accurate")
                assert embed == "sentence-transformers/all-mpnet-base-v2"
                assert reranker == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    def test_live_retrieve_uses_model_config(self):
        """Test that live retrieval uses model configuration."""
        config_yaml = """
fast:
  embed_model: sentence-transformers/all-MiniLM-L6-v2
  reranker_model: null

accurate:
  embed_model: sentence-transformers/all-mpnet-base-v2
  reranker_model: cross-encoder/ms-marco-electra-base
"""
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            adapter = RAGAdapter()
            
            # Mock FAISS store
            mock_store = MagicMock()
            mock_store.search.return_value = [(0, 0.9), (1, 0.8)]
            mock_store.get_meta.return_value = {"doc": "test_doc", "chunk": 1, "text": "test text"}
            mock_store.get_embedder_name.return_value = "sentence-transformers/all-MiniLM-L6-v2"
            mock_store.get_index_info.return_value = {"path": "test", "dim": 384, "count": 100}
            mock_store.get_reranker_name.return_value = None
            
            adapter.faiss_stores = {"fast": mock_store}
            
            # Test fast lane retrieval
            results = adapter._live_retrieve("test query", "fast")
            
            # Verify that the store was used
            mock_store.search.assert_called_once()
            mock_store.get_embedder_name.assert_called_once()
    
    def test_accurate_lane_reranker_model_selection(self):
        """Test that accurate lane uses the correct reranker model."""
        config_yaml = """
accurate:
  embed_model: sentence-transformers/all-mpnet-base-v2
  reranker_model: cross-encoder/ms-marco-electra-base
"""
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            adapter = RAGAdapter()
            
            # Mock FAISS store
            mock_store = MagicMock()
            mock_store.search.return_value = [(0, 0.9), (1, 0.8)]
            mock_store.get_meta.return_value = {"doc": "test_doc", "chunk": 1, "text": "test text"}
            mock_store.get_embedder_name.return_value = "sentence-transformers/all-mpnet-base-v2"
            mock_store.get_index_info.return_value = {"path": "test", "dim": 768, "count": 100}
            mock_store.get_reranker_name.return_value = "cross-encoder/ms-marco-electra-base"
            mock_store.rerank_with_cross_encoder.return_value = [(0, 0.95), (1, 0.85)]
            
            adapter.faiss_stores = {"accurate": mock_store}
            
            # Test accurate lane retrieval
            results = adapter._live_retrieve("test query", "accurate")
            
            # Verify that reranking was called with the correct model
            mock_store.rerank_with_cross_encoder.assert_called_once()
            call_args = mock_store.rerank_with_cross_encoder.call_args
            assert call_args[0][2] == "cross-encoder/ms-marco-electra-base"  # model_name argument
    
    def test_accurate_lane_fallback_reranker(self):
        """Test that accurate lane falls back to default reranker when none configured."""
        config_yaml = """
accurate:
  embed_model: sentence-transformers/all-mpnet-base-v2
  reranker_model: null
"""
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            adapter = RAGAdapter()
            
            # Mock FAISS store
            mock_store = MagicMock()
            mock_store.search.return_value = [(0, 0.9), (1, 0.8)]
            mock_store.get_meta.return_value = {"doc": "test_doc", "chunk": 1, "text": "test text"}
            mock_store.get_embedder_name.return_value = "sentence-transformers/all-mpnet-base-v2"
            mock_store.get_index_info.return_value = {"path": "test", "dim": 768, "count": 100}
            mock_store.get_reranker_name.return_value = None
            mock_store.rerank_with_cross_encoder.return_value = [(0, 0.95), (1, 0.85)]
            
            adapter.faiss_stores = {"accurate": mock_store}
            
            # Test accurate lane retrieval
            results = adapter._live_retrieve("test query", "accurate")
            
            # Verify that fallback reranker was used
            mock_store.rerank_with_cross_encoder.assert_called_once()
            call_args = mock_store.rerank_with_cross_encoder.call_args
            assert call_args[0][2] == "cross-encoder/ms-marco-electra-base"  # fallback model
    
    def test_to_log_dict_includes_model_info(self):
        """Test that to_log_dict includes model information."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            adapter = RAGAdapter()
            
            # Mock FAISS store
            mock_store = MagicMock()
            mock_store.get_embedder_name.return_value = "sentence-transformers/all-MiniLM-L6-v2"
            mock_store.get_index_info.return_value = {"path": "test", "dim": 384, "count": 100}
            mock_store.get_reranker_name.return_value = None
            
            adapter.faiss_stores = {"fast": mock_store}
            
            # Test log dict generation
            results = [{"rank": 1, "doc": "test_doc", "chunk": 1, "score": 0.9}]
            log_dict = adapter.to_log_dict(results, 100.0, 50.0, "fast")
            
            # Verify model information is included
            assert "retrieval" in log_dict
            assert log_dict["retrieval"]["embed_model"] == "sentence-transformers/all-MiniLM-L6-v2"
            assert log_dict["retrieval"]["reranker_model"] is None
    
    def test_dummy_mode_does_not_require_model_config(self):
        """Test that dummy mode works without model configuration."""
        with patch.dict(os.environ, {'USE_DUMMY_RAG': '1'}):
            with patch('builtins.open', side_effect=FileNotFoundError):
                adapter = RAGAdapter()
                
                # Should still have model config
                assert hasattr(adapter, 'model_config')
                
                # Should work in dummy mode
                assert adapter.dummy_mode is True
                
                # Should return empty results
                results = adapter.retrieve("test query", "fast")
                assert results == []


def mock_open(read_data):
    """Helper function to create a mock file object."""
    from unittest.mock import mock_open as _mock_open
    return _mock_open(read_data=read_data)


if __name__ == "__main__":
    pytest.main([__file__])
