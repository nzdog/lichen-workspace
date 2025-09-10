"""
Completion Module
Implements Completion Prompt Required behavior from Entry Room Protocol
"""

from .types import CompletionPolicy


class DefaultCompletionPolicy(CompletionPolicy):
    """Default completion policy with standard marker"""
    
    def append_completion_marker(self, text: str) -> str:
        """Appends a completion marker to the display text"""
        marker = '\n\n[✓ Entry Room Complete]'
        return text + marker


class MinimalCompletionPolicy(CompletionPolicy):
    """Minimal completion policy with simple marker"""
    
    def append_completion_marker(self, text: str) -> str:
        """Appends a minimal completion marker"""
        marker = '\n[✓]'
        return text + marker


class VerboseCompletionPolicy(CompletionPolicy):
    """Verbose completion policy with detailed marker"""
    
    def append_completion_marker(self, text: str) -> str:
        """Appends a verbose completion marker"""
        marker = '\n\n--- Entry Room Session Complete ---\nReady for next phase.'
        return text + marker


class CustomCompletionPolicy(CompletionPolicy):
    """Custom completion policy with configurable marker"""
    
    def __init__(self, marker: str = '[✓ Entry Room Complete]'):
        self.marker = marker
    
    def append_completion_marker(self, text: str) -> str:
        """Appends a custom completion marker"""
        return text + '\n\n' + self.marker


def has_completion_marker(text: str) -> bool:
    """Utility function to check if text already has a completion marker"""
    markers = [
        '[✓ Entry Room Complete]',
        '[✓]',
        '--- Entry Room Session Complete ---',
        'Entry Room Complete'
    ]
    
    return any(marker in text for marker in markers)


def remove_completion_markers(text: str) -> str:
    """Utility function to remove existing completion markers"""
    import re
    
    markers = [
        r'\[✓ Entry Room Complete\].*$',
        r'\[✓\].*$',
        r'--- Entry Room Session Complete ---.*$',
        r'Entry Room Session Complete.*$'
    ]
    
    cleaned_text = text
    for pattern in markers:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.DOTALL)
    
    return cleaned_text.strip()
