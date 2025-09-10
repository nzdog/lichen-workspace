"""
Reflection Module
Implements Faithful Reflection theme from Entry Room Protocol
"""

from typing import List, Any
from .types import ReflectionPolicy


class VerbatimReflection(ReflectionPolicy):
    """
    Reflects input exactly without interpretation or distortion.
    If multiple ideas are present, returns one per line in order.
    No paraphrase or summarization.
    """
    
    def reflect_verbatim(self, payload: Any) -> List[str]:
        """Reflects input exactly without interpretation or distortion"""
        if payload is None:
            return ['No input provided']
        
        if isinstance(payload, str):
            return self._split_multiple_ideas(payload)
        
        if isinstance(payload, dict):
            return self._extract_text_from_object(payload)
        
        return [str(payload)]
    
    def _split_multiple_ideas(self, text: str) -> List[str]:
        """Split text by line breaks while preserving order"""
        # Split only on actual line breaks to preserve original formatting
        lines = [
            line.strip() for line in text.split('\n')
            if line.strip()
        ]
        
        # If no line breaks, return as single idea
        if len(lines) <= 1:
            return [text.strip()]
        
        return lines
    
    def _extract_text_from_object(self, obj: dict) -> List[str]:
        """Extract text from object payloads"""
        ideas = []
        
        # Handle common object patterns
        if 'text' in obj and isinstance(obj['text'], str):
            ideas.extend(self._split_multiple_ideas(obj['text']))
        elif 'message' in obj and isinstance(obj['message'], str):
            ideas.extend(self._split_multiple_ideas(obj['message']))
        elif 'content' in obj and isinstance(obj['content'], str):
            ideas.extend(self._split_multiple_ideas(obj['content']))
        else:
            # Fallback: stringify and split
            json_str = str(obj)
            ideas.extend(self._split_multiple_ideas(json_str))
        
        return ideas
