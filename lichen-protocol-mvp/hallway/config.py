"""
Configuration management for the Hallway Protocol.
"""

import os
from typing import Dict, Any, Optional


def env_bool(key: str, default: bool = False) -> bool:
    """Convert environment variable to boolean."""
    value = os.getenv(key, "").lower()
    return value in ("1", "true", "yes", "on")


def get_rag_escalation_config() -> Dict[str, Any]:
    """
    Get RAG escalation configuration with defaults and environment overrides.
    
    Returns:
        Dict with escalation configuration
    """
    return {
        "grounding_threshold": float(os.getenv("RAG_GROUNDING_THRESHOLD", "0.65")),
        "complexity_threshold": float(os.getenv("RAG_COMPLEXITY_THRESHOLD", "0.7")),
        "disable": env_bool("RAG_DISABLE_ESCALATION", False),
        "force_lane": os.getenv("RAG_FORCE_LANE", "").lower()  # "fast" or "accurate"
    }


def get_rag_config() -> Dict[str, Any]:
    """
    Get complete RAG configuration including escalation settings.
    
    Returns:
        Dict with all RAG configuration
    """
    return {
        "escalation": get_rag_escalation_config(),
        "min_grounding": float(os.getenv("MIN_GROUNDING", "0.25")),
        "default_lane": os.getenv("RAG_DEFAULT_LANE", "fast")
    }
