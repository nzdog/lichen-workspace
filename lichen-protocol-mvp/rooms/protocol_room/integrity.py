"""
Integrity Module
Implements Integrity Gate theme from Protocol Room Protocol
"""

from typing import List
from .room_types import IntegrityResult


def check_stones_alignment(protocol_text: str) -> bool:
    """
    Check if protocol aligns with Stones principles.
    Stub implementation - in production this would be more sophisticated.
    """
    # Simple deterministic checks
    text_lower = protocol_text.lower()
    
    # Check for integrity-related language
    integrity_indicators = [
        "integrity", "honesty", "authenticity", "truth",
        "clarity", "simplicity", "directness",
        "care", "respect", "safety", "trust",
        "help", "support", "guide", "assist", "enable"
    ]
    
    # Check for potential misalignment indicators
    misalignment_indicators = [
        "manipulation", "deception", "complexity", "confusion",
        "pressure", "urgency", "demand", "force", "coerce"
    ]
    
    # Count positive indicators
    positive_count = sum(1 for indicator in integrity_indicators if indicator in text_lower)
    
    # Count negative indicators
    negative_count = sum(1 for indicator in misalignment_indicators if indicator in text_lower)
    
    # More lenient scoring: protocols are aligned by default unless they have clear misalignment
    # Give a baseline score for well-structured protocols
    baseline_score = 2 if any(word in text_lower for word in ['purpose', 'step', 'help', 'guide']) else 0
    
    total_score = positive_count + baseline_score
    return total_score >= negative_count


def check_coherence(protocol_text: str) -> bool:
    """
    Check if protocol text is coherent and well-structured.
    Stub implementation - in production this would be more sophisticated.
    """
    # Simple deterministic checks
    text_lines = protocol_text.split('\n')
    
    # Check for reasonable length - be more lenient
    reasonable_length = 20 <= len(protocol_text) <= 10000
    
    # Check for clear language - be more lenient
    clear_language = not any(word in protocol_text.lower() for word in ['jargon', 'confusing', 'unclear'])
    
    # For scenario text (single line), just check length and clarity
    if len(text_lines) <= 2:
        # But still check for some basic structure indicators
        has_basic_structure = any(word in protocol_text.lower() for word in ['purpose', 'step', 'help', 'guide', 'when', 'take'])
        return reasonable_length and clear_language and has_basic_structure
    
    # For full protocols, check for structure
    has_title = any(line.startswith('#') for line in text_lines)
    has_steps = any('step' in line.lower() or '1.' in line or '2.' in line or '**' in line for line in text_lines)
    
    # Must have basic structure elements for full protocols
    return has_title and has_steps and reasonable_length and clear_language


def run_integrity_gate(protocol_text: str) -> IntegrityResult:
    """
    Run protocol through integrity gate checks.
    Includes Stones alignment and coherence checks.
    """
    stones_aligned = check_stones_alignment(protocol_text)
    coherent = check_coherence(protocol_text)
    
    # Both checks must pass
    passed = stones_aligned and coherent
    
    # Generate notes
    notes = []
    if not stones_aligned:
        notes.append("Protocol does not align with Stones principles")
    if not coherent:
        notes.append("Protocol lacks coherence or structure")
    if passed:
        notes.append("Protocol passed all integrity checks")
    
    return IntegrityResult(
        passed=passed,
        stones_aligned=stones_aligned,
        coherent=coherent,
        notes=notes
    )


def validate_protocol_delivery(protocol_text: str) -> IntegrityResult:
    """
    Validate that protocol is safe for delivery.
    This is the main integrity check function.
    """
    return run_integrity_gate(protocol_text)
