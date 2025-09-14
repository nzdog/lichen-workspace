"""
Type definitions for AI Room
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union


@dataclass
class AIRoomInput:
    """Input structure for AI Room"""
    session_state_ref: str
    payload: Optional[Dict[str, Any]] = None
    brief: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class AIRoomOutput:
    """Output structure for AI Room"""
    display_text: str
    next_action: str = "continue"
    meta: Optional[Dict[str, Any]] = None


@dataclass
class AIRoomContext:
    """Context for AI Room execution"""
    session_state_ref: str
    brief: Dict[str, Any]
    context: Optional[Dict[str, Any]]
    is_first_retrieval: bool = False


@dataclass
class RAGResult:
    """RAG retrieval and generation result"""
    query: str
    lane: str
    retrieved_docs: List[Dict[str, Any]]
    generated_answer: str
    citations: List[Dict[str, Any]]
    grounding_score: float
    stones_alignment: float
    hallucinations: int
    insufficient_support: bool


@dataclass
class ConsentPrompt:
    """Consent/trust seal prompt for first retrieval"""
    text: str
    required: bool = True
