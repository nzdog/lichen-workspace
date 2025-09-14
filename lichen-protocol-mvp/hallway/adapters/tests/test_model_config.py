"""
Unit tests for model configuration management.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from ..model_config import ModelConfig, get_model_config, get_active_model_ids, get_all_active_model_ids


class TestModelConfig:
    """Test cases for ModelConfig class."""
    
    def test_default_config(self):
        """Test default configuration when no config file exists."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            config = ModelConfig()
            
            # Test fast lane
            embed, reranker = config.get_model_ids("fast")
            assert embed == "sentence-transformers/all-MiniLM-L6-v2"
            assert reranker is None
            
            # Test accurate lane
            embed, reranker = config.get_model_ids("accurate")
            assert embed == "sentence-transformers/all-mpnet-base-v2"
            assert reranker == "cross-encoder/ms-marco-electra-base"
    
    def test_config_file_loading(self):
        """Test loading configuration from YAML file."""
        config_yaml = """
fast:
  embed_model: sentence-transformers/all-MiniLM-L12-v2
  reranker_model: null

accurate:
  embed_model: intfloat/e5-large-v2
  reranker_model: cross-encoder/ms-marco-MiniLM-L-6-v2

model_info:
  sentence-transformers/all-MiniLM-L12-v2:
    dimensions: 384
    description: "Higher quality MiniLM model"
"""
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            config = ModelConfig()
            
            # Test fast lane
            embed, reranker = config.get_model_ids("fast")
            assert embed == "sentence-transformers/all-MiniLM-L12-v2"
            assert reranker is None
            
            # Test accurate lane
            embed, reranker = config.get_model_ids("accurate")
            assert embed == "intfloat/e5-large-v2"
            assert reranker == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    def test_environment_variable_overrides(self):
        """Test environment variable overrides."""
        config_yaml = """
fast:
  embed_model: sentence-transformers/all-MiniLM-L6-v2
  reranker_model: null

accurate:
  embed_model: sentence-transformers/all-mpnet-base-v2
  reranker_model: cross-encoder/ms-marco-electra-base
"""
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            with patch.dict(os.environ, {
                'RAG_FAST_EMBED': 'sentence-transformers/all-MiniLM-L12-v2',
                'RAG_ACCURATE_RERANK': 'cross-encoder/ms-marco-MiniLM-L-6-v2'
            }):
                config = ModelConfig()
                
                # Test fast lane with embed override
                embed, reranker = config.get_model_ids("fast")
                assert embed == "sentence-transformers/all-MiniLM-L12-v2"
                assert reranker is None
                
                # Test accurate lane with reranker override
                embed, reranker = config.get_model_ids("accurate")
                assert embed == "sentence-transformers/all-mpnet-base-v2"
                assert reranker == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    def test_environment_variable_null_handling(self):
        """Test handling of null values in environment variables."""
        config_yaml = """
fast:
  embed_model: sentence-transformers/all-MiniLM-L6-v2
  reranker_model: null

accurate:
  embed_model: sentence-transformers/all-mpnet-base-v2
  reranker_model: cross-encoder/ms-marco-electra-base
"""
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            with patch.dict(os.environ, {
                'RAG_FAST_EMBED': 'null',
                'RAG_ACCURATE_RERANK': 'none'
            }):
                config = ModelConfig()
                
                # Test null handling
                embed, reranker = config.get_model_ids("fast")
                assert embed is None
                assert reranker is None
                
                embed, reranker = config.get_model_ids("accurate")
                assert embed == "sentence-transformers/all-mpnet-base-v2"
                assert reranker is None
    
    def test_get_embed_model(self):
        """Test get_embed_model method."""
        config_yaml = """
fast:
  embed_model: sentence-transformers/all-MiniLM-L6-v2
  reranker_model: null
"""
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            config = ModelConfig()
            assert config.get_embed_model("fast") == "sentence-transformers/all-MiniLM-L6-v2"
    
    def test_get_reranker_model(self):
        """Test get_reranker_model method."""
        config_yaml = """
accurate:
  embed_model: sentence-transformers/all-mpnet-base-v2
  reranker_model: cross-encoder/ms-marco-electra-base
"""
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            config = ModelConfig()
            assert config.get_reranker_model("accurate") == "cross-encoder/ms-marco-electra-base"
            assert config.get_reranker_model("fast") is None
    
    def test_get_all_model_ids(self):
        """Test get_all_model_ids method."""
        config_yaml = """
fast:
  embed_model: sentence-transformers/all-MiniLM-L6-v2
  reranker_model: null

accurate:
  embed_model: sentence-transformers/all-mpnet-base-v2
  reranker_model: cross-encoder/ms-marco-electra-base
"""
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            config = ModelConfig()
            all_ids = config.get_all_model_ids()
            
            assert all_ids["fast"]["embed_model"] == "sentence-transformers/all-MiniLM-L6-v2"
            assert all_ids["fast"]["reranker_model"] is None
            assert all_ids["accurate"]["embed_model"] == "sentence-transformers/all-mpnet-base-v2"
            assert all_ids["accurate"]["reranker_model"] == "cross-encoder/ms-marco-electra-base"
    
    def test_get_model_info(self):
        """Test get_model_info method."""
        config_yaml = """
model_info:
  sentence-transformers/all-MiniLM-L6-v2:
    dimensions: 384
    description: "Fast, lightweight embedding model"
    use_case: "Fast lane, low latency"
"""
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            config = ModelConfig()
            
            # Test known model
            info = config.get_model_info("sentence-transformers/all-MiniLM-L6-v2")
            assert info["dimensions"] == 384
            assert info["description"] == "Fast, lightweight embedding model"
            assert info["use_case"] == "Fast lane, low latency"
            
            # Test unknown model
            info = config.get_model_info("unknown-model")
            assert info["dimensions"] == "unknown"
            assert info["description"] == "Unknown model"
            assert info["use_case"] == "Unknown"
    
    def test_validate_model_config(self):
        """Test model configuration validation."""
        config_yaml = """
fast:
  embed_model: sentence-transformers/all-MiniLM-L6-v2
  reranker_model: null

accurate:
  embed_model: sentence-transformers/all-mpnet-base-v2
  reranker_model: cross-encoder/ms-marco-electra-base
"""
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            config = ModelConfig()
            validation = config.validate_model_config()
            
            assert validation["valid"] is True
            assert len(validation["errors"]) == 0
            assert validation["lanes"]["fast"]["valid"] is True
            assert validation["lanes"]["accurate"]["valid"] is True
    
    def test_validate_model_config_with_errors(self):
        """Test model configuration validation with errors."""
        config_yaml = """
fast:
  embed_model: ""
  reranker_model: null

accurate:
  embed_model: sentence-transformers/all-mpnet-base-v2
  reranker_model: cross-encoder/ms-marco-electra-base
"""
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            config = ModelConfig()
            validation = config.validate_model_config()
            
            assert validation["valid"] is False
            assert len(validation["errors"]) > 0
            assert any("No embedding model configured for fast lane" in error for error in validation["errors"])
    
    def test_caching(self):
        """Test that model IDs are cached correctly."""
        config_yaml = """
fast:
  embed_model: sentence-transformers/all-MiniLM-L6-v2
  reranker_model: null
"""
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            config = ModelConfig()
            
            # First call should populate cache
            embed1, reranker1 = config.get_model_ids("fast")
            
            # Second call should use cache
            embed2, reranker2 = config.get_model_ids("fast")
            
            assert embed1 == embed2
            assert reranker1 == reranker2
            assert "fast" in config._cache


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    def test_get_model_config_singleton(self):
        """Test that get_model_config returns a singleton."""
        config1 = get_model_config()
        config2 = get_model_config()
        assert config1 is config2
    
    def test_get_active_model_ids(self):
        """Test get_active_model_ids convenience function."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            embed, reranker = get_active_model_ids("fast")
            assert embed == "sentence-transformers/all-MiniLM-L6-v2"
            assert reranker is None
    
    def test_get_all_active_model_ids(self):
        """Test get_all_active_model_ids convenience function."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            all_ids = get_all_active_model_ids()
            assert "fast" in all_ids
            assert "accurate" in all_ids
            assert all_ids["fast"]["embed_model"] == "sentence-transformers/all-MiniLM-L6-v2"
            assert all_ids["accurate"]["embed_model"] == "sentence-transformers/all-mpnet-base-v2"


class TestConfigPrecedence:
    """Test configuration precedence (env > config > defaults)."""
    
    def test_precedence_order(self):
        """Test that environment variables override config file which overrides defaults."""
        config_yaml = """
fast:
  embed_model: sentence-transformers/all-MiniLM-L12-v2
  reranker_model: null
"""
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            with patch.dict(os.environ, {
                'RAG_FAST_EMBED': 'sentence-transformers/all-MiniLM-L6-v2'
            }):
                config = ModelConfig()
                embed, reranker = config.get_model_ids("fast")
                
                # Environment variable should override config file
                assert embed == "sentence-transformers/all-MiniLM-L6-v2"
                assert reranker is None
    
    def test_missing_config_falls_back_to_defaults(self):
        """Test that missing config values fall back to defaults."""
        config_yaml = """
fast:
  embed_model: sentence-transformers/all-MiniLM-L12-v2
  # reranker_model missing - should fall back to default (null)
"""
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            config = ModelConfig()
            embed, reranker = config.get_model_ids("fast")
            
            # Should use config value for embed, default for reranker
            assert embed == "sentence-transformers/all-MiniLM-L12-v2"
            assert reranker is None


if __name__ == "__main__":
    pytest.main([__file__])
