"""
Model configuration management for RAG lanes.

Provides a single source of truth for model IDs per lane with environment variable overrides.
Supports the model swap readiness feature with configurable embedding and reranker models.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class ModelConfig:
    """Model configuration manager with environment variable overrides."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize model configuration."""
        self.config = self._load_config(config_path)
        self._cache = {}  # Cache for resolved model IDs
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load model configuration from YAML file."""
        if config_path is None:
            # Try multiple possible config paths
            config_paths = [
                Path("config/models.yaml"),
                Path("../config/models.yaml"),
                Path("../../config/models.yaml"),
            ]
            
            for path in config_paths:
                if path.exists():
                    config_path = str(path)
                    break
            else:
                # Return default config if no file found
                logger.warning("No models.yaml found, using default configuration")
                return self._get_default_config()
        
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load model config from {config_path}: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default model configuration."""
        return {
            "fast": {
                "embed_model": "sentence-transformers/all-MiniLM-L6-v2",
                "reranker_model": None
            },
            "accurate": {
                "embed_model": "sentence-transformers/all-mpnet-base-v2",
                "reranker_model": "cross-encoder/ms-marco-electra-base"
            }
        }
    
    def get_model_ids(self, lane: str) -> Tuple[str, Optional[str]]:
        """
        Get the active embedding and reranker model IDs for a lane.
        
        Args:
            lane: Lane name (fast/accurate)
            
        Returns:
            Tuple of (embed_model_id, reranker_model_id)
        """
        if lane in self._cache:
            return self._cache[lane]
        
        # Get base config for lane
        lane_config = self.config.get(lane, {})
        
        # Apply environment variable overrides
        embed_model = self._get_env_override(f"RAG_{lane.upper()}_EMBED", 
                                           lane_config.get("embed_model"))
        reranker_model = self._get_env_override(f"RAG_{lane.upper()}_RERANK", 
                                              lane_config.get("reranker_model"))
        
        # Cache the result
        result = (embed_model, reranker_model)
        self._cache[lane] = result
        
        logger.debug(f"Resolved {lane} lane models: embed={embed_model}, reranker={reranker_model}")
        return result
    
    def _get_env_override(self, env_key: str, default_value: Any) -> Any:
        """Get environment variable override or return default value."""
        env_value = os.getenv(env_key)
        if env_value is not None:
            # Handle None/null values from environment
            if env_value.lower() in ('null', 'none', ''):
                return None
            return env_value
        return default_value
    
    def get_embed_model(self, lane: str) -> str:
        """Get the embedding model ID for a lane."""
        embed_model, _ = self.get_model_ids(lane)
        return embed_model
    
    def get_reranker_model(self, lane: str) -> Optional[str]:
        """Get the reranker model ID for a lane."""
        _, reranker_model = self.get_model_ids(lane)
        return reranker_model
    
    def get_all_model_ids(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active model IDs for all lanes.
        
        Returns:
            Dict mapping lane names to their model configurations
        """
        return {
            "fast": {
                "embed_model": self.get_embed_model("fast"),
                "reranker_model": self.get_reranker_model("fast")
            },
            "accurate": {
                "embed_model": self.get_embed_model("accurate"),
                "reranker_model": self.get_reranker_model("accurate")
            }
        }
    
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """
        Get metadata information for a model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Dict with model metadata (dimensions, description, use_case)
        """
        model_info = self.config.get("model_info", {})
        return model_info.get(model_id, {
            "dimensions": "unknown",
            "description": "Unknown model",
            "use_case": "Unknown"
        })
    
    def validate_model_config(self) -> Dict[str, Any]:
        """
        Validate the current model configuration.
        
        Returns:
            Dict with validation results
        """
        validation = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "lanes": {}
        }
        
        for lane in ["fast", "accurate"]:
            lane_validation = {"valid": True, "errors": [], "warnings": []}
            
            try:
                embed_model, reranker_model = self.get_model_ids(lane)
                
                if not embed_model:
                    lane_validation["valid"] = False
                    lane_validation["errors"].append(f"No embedding model configured for {lane} lane")
                
                # Check if reranker is expected for accurate lane
                if lane == "accurate" and not reranker_model:
                    lane_validation["warnings"].append(f"No reranker model configured for {lane} lane (may impact quality)")
                
                # Check if reranker is unexpected for fast lane
                if lane == "fast" and reranker_model:
                    lane_validation["warnings"].append(f"Reranker model configured for {lane} lane (may impact speed)")
                
            except Exception as e:
                lane_validation["valid"] = False
                lane_validation["errors"].append(f"Failed to resolve models for {lane} lane: {e}")
            
            validation["lanes"][lane] = lane_validation
            
            if not lane_validation["valid"]:
                validation["valid"] = False
                validation["errors"].extend(lane_validation["errors"])
            
            validation["warnings"].extend(lane_validation["warnings"])
        
        return validation


# Global instance for easy access
_model_config = None


def get_model_config() -> ModelConfig:
    """Get the global model configuration instance."""
    global _model_config
    if _model_config is None:
        _model_config = ModelConfig()
    return _model_config


def get_active_model_ids(lane: str) -> Tuple[str, Optional[str]]:
    """Get the active model IDs for a lane (convenience function)."""
    return get_model_config().get_model_ids(lane)


def get_all_active_model_ids() -> Dict[str, Dict[str, Any]]:
    """Get all active model IDs for all lanes (convenience function)."""
    return get_model_config().get_all_model_ids()
