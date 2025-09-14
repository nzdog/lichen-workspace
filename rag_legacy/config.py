"""
Configuration resolution for RAG system.

Provides utilities for resolving configuration from environment variables,
YAML files, and defaults with proper precedence.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Configuration dictionary
    """
    config_path = Path(config_path)
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}")
        return {}
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded config from: {config_path}")
        return config or {}
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return {}


def resolve_config(config_path: str = "config/rag.yaml") -> Dict[str, Any]:
    """
    Resolve configuration with precedence: env > yaml > defaults.
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Resolved configuration dictionary
    """
    # Default configuration
    defaults = {
        # Model configurations
        "embed_model_fast": "sentence-transformers/all-MiniLM-L6-v2",
        "embed_model_accurate": "sentence-transformers/all-MiniLM-L6-v2",
        "cross_encoder_model": "",
        
        # Index paths
        "fast_index_path": "data/indexes/vecs_fast.faiss",
        "fast_stats_path": "data/indexes/vecs_fast.stats.json",
        "fast_meta_path": "data/indexes/vecs_fast.meta.jsonl",
        "accurate_index_path": "data/indexes/vecs_accurate.faiss",
        "accurate_stats_path": "data/indexes/vecs_accurate.stats.json",
        "accurate_meta_path": "data/indexes/vecs_accurate.meta.jsonl",
        
        # Protocol catalog
        "protocol_catalog_path": "data/protocol_catalog.json",
        
        # Retrieval parameters
        "k_dense": 200,
        "k_lex": 200,
        "rrf_c": 60,
        "protocol_topn": 10,
        "protocol_boost": 0.15,
        "stone_boost": 0.05,
        "fast_return": 8,
        "accurate_in": 60,
        "accurate_out": 8,
        
        # Router configuration
        "router_hard_gate": 0,  # 0 = soft routing, 1 = hard gating
        "rag_strategy": "protocol_first_hybrid",
        
        # Offline configuration
        "hf_hub_offline": "1",
        "transformers_offline": "1",
        "sentence_transformers_home": "~/.cache/sentence_transformers"
    }
    
    # Load YAML config
    yaml_config = load_yaml_config(config_path)
    
    # Environment variable mappings
    env_mappings = {
        # Model configurations
        "EMBED_MODEL_FAST": "embed_model_fast",
        "EMBED_MODEL_ACCURATE": "embed_model_accurate",
        "CROSS_ENCODER_MODEL": "cross_encoder_model",
        
        # Index paths
        "FAST_INDEX_PATH": "fast_index_path",
        "FAST_STATS_PATH": "fast_stats_path",
        "FAST_META_PATH": "fast_meta_path",
        "ACCURATE_INDEX_PATH": "accurate_index_path",
        "ACCURATE_STATS_PATH": "accurate_stats_path",
        "ACCURATE_META_PATH": "accurate_meta_path",
        
        # Protocol catalog
        "PROTOCOL_CATALOG_PATH": "protocol_catalog_path",
        
        # Retrieval parameters
        "K_DENSE": "k_dense",
        "K_LEX": "k_lex",
        "RRF_C": "rrf_c",
        "PROTOCOL_TOPN": "protocol_topn",
        "PROTOCOL_BOOST": "protocol_boost",
        "STONE_BOOST": "stone_boost",
        "FAST_RETURN": "fast_return",
        "ACCURATE_IN": "accurate_in",
        "ACCURATE_OUT": "accurate_out",
        
        # Router configuration
        "ROUTER_HARD_GATE": "router_hard_gate",
        "RAG_STRATEGY": "rag_strategy",
        
        # Offline configuration
        "HF_HUB_OFFLINE": "hf_hub_offline",
        "TRANSFORMERS_OFFLINE": "transformers_offline",
        "SENTENCE_TRANSFORMERS_HOME": "sentence_transformers_home"
    }
    
    # Start with defaults
    config = defaults.copy()
    
    # Apply YAML config
    config.update(yaml_config)
    
    # Apply environment variables (highest precedence)
    for env_var, config_key in env_mappings.items():
        env_value = os.getenv(env_var)
        if env_value is not None:
            # Convert string values to appropriate types
            if config_key in ["k_dense", "k_lex", "rrf_c", "protocol_topn", "fast_return", "accurate_in", "accurate_out", "router_hard_gate"]:
                try:
                    config[config_key] = int(env_value)
                except ValueError:
                    logger.warning(f"Invalid integer value for {env_var}: {env_value}")
            elif config_key in ["protocol_boost", "stone_boost"]:
                try:
                    config[config_key] = float(env_value)
                except ValueError:
                    logger.warning(f"Invalid float value for {env_var}: {env_value}")
            else:
                config[config_key] = env_value
    
    # Set offline environment variables if configured
    if config.get("hf_hub_offline"):
        os.environ["HF_HUB_OFFLINE"] = str(config["hf_hub_offline"])
    if config.get("transformers_offline"):
        os.environ["TRANSFORMERS_OFFLINE"] = str(config["transformers_offline"])
    if config.get("sentence_transformers_home"):
        home_path = str(config["sentence_transformers_home"]).replace("~", os.path.expanduser("~"))
        os.environ["SENTENCE_TRANSFORMERS_HOME"] = home_path
    
    logger.info("Configuration resolved successfully")
    return config


def get_config_value(key: str, default: Any = None, config_path: str = "config/rag.yaml") -> Any:
    """
    Get a single configuration value.
    
    Args:
        key: Configuration key
        default: Default value if key not found
        config_path: Path to YAML configuration file
        
    Returns:
        Configuration value
    """
    config = resolve_config(config_path)
    return config.get(key, default)


def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate configuration and return list of issues.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of validation issues (empty if valid)
    """
    issues = []
    
    # Check required paths exist
    required_paths = [
        "fast_index_path", "fast_stats_path",
        "accurate_index_path", "accurate_stats_path",
        "protocol_catalog_path"
    ]
    
    for path_key in required_paths:
        path = config.get(path_key)
        if path and not Path(path).exists():
            issues.append(f"Required path not found: {path_key}={path}")
    
    # Check numeric ranges
    numeric_checks = [
        ("k_dense", 1, 1000),
        ("k_lex", 1, 1000),
        ("rrf_c", 1, 1000),
        ("protocol_topn", 1, 100),
        ("protocol_boost", 0.0, 1.0),
        ("stone_boost", 0.0, 1.0),
        ("fast_return", 1, 50),
        ("accurate_out", 1, 50)
    ]
    
    for key, min_val, max_val in numeric_checks:
        value = config.get(key)
        if value is not None:
            if not isinstance(value, (int, float)) or value < min_val or value > max_val:
                issues.append(f"Invalid value for {key}: {value} (expected {min_val}-{max_val})")
    
    return issues


def print_config_summary(config: Dict[str, Any]):
    """Print a summary of the current configuration."""
    print("RAG Configuration Summary")
    print("=" * 50)
    
    # Model configuration
    print("Models:")
    print(f"  Fast embedder: {config.get('embed_model_fast')}")
    print(f"  Accurate embedder: {config.get('embed_model_accurate')}")
    print(f"  Cross-encoder: {config.get('cross_encoder_model', 'None')}")
    
    # Index paths
    print("\nIndex Paths:")
    print(f"  Fast index: {config.get('fast_index_path')}")
    print(f"  Accurate index: {config.get('accurate_index_path')}")
    print(f"  Protocol catalog: {config.get('protocol_catalog_path')}")
    
    # Retrieval parameters
    print("\nRetrieval Parameters:")
    print(f"  K dense: {config.get('k_dense')}")
    print(f"  K lex: {config.get('k_lex')}")
    print(f"  RRF C: {config.get('rrf_c')}")
    print(f"  Protocol boost: {config.get('protocol_boost')}")
    print(f"  Stone boost: {config.get('stone_boost')}")
    
    # Router configuration
    print("\nRouter Configuration:")
    print(f"  Hard gate: {config.get('router_hard_gate')}")
    print(f"  RAG strategy: {config.get('rag_strategy')}")
    
    # Validation
    issues = validate_config(config)
    if issues:
        print(f"\n⚠️  Configuration Issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ Configuration is valid")


if __name__ == "__main__":
    # Print configuration when run as script
    config = resolve_config()
    print_config_summary(config)
