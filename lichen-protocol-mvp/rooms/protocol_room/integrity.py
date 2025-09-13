"""
Integrity Module
Implements Integrity Gate theme from Protocol Room Protocol
"""

import os
import json
from pprint import pformat
from typing import List, Dict, Any
from .types import IntegrityResult

INTEGRITY_DEBUG = os.getenv("INTEGRITY_DEBUG", "0") in {"1", "true", "True", "YES", "yes"}

def _dprint(*args, **kwargs):
    if INTEGRITY_DEBUG:
        print(*args, **kwargs)


def check_stones_alignment(protocol_data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Check if protocol aligns with Stones principles.
    Returns (aligned: bool, reasons: List[str])
    """
    protocol_id = (protocol_data or {}).get("Protocol ID", "<unknown>")
    stones = (protocol_data.get("Metadata", {}) or {}).get("Stones", [])
    
    _dprint(f"[INTEGRITY] Stones check start  | id={protocol_id}")
    _dprint("  Stones provided:", stones)
    
    reasons = []
    
    # Check if Stones list exists and has sufficient content
    if not stones:
        reasons.append("No Stones specified in Metadata")
        _dprint(f"[INTEGRITY] Stones check result | id={protocol_id} aligned=False")
        _dprint("  Stones reasons:\n", pformat(reasons))
        return False, reasons
    
    if len(stones) < 2:
        reasons.append(f"Too few Stones specified ({len(stones)}). Need at least 2.")
    
    # Check for required Stones
    required_stones = ["the-speed-of-trust", "clarity-over-cleverness"]
    missing_stones = [stone for stone in required_stones if stone not in stones]
    if missing_stones:
        reasons.append(f"Missing required Stones: {missing_stones}")
    
    # Check for Stones alignment with protocol content
    protocol_text = json.dumps(protocol_data, default=str).lower()
    
    # Check for integrity-related language
    integrity_indicators = [
        "integrity", "honesty", "authenticity", "truth",
        "clarity", "simplicity", "directness",
        "care", "respect", "safety", "trust", "presence"
    ]
    
    # Check for potential misalignment indicators
    misalignment_indicators = [
        "manipulation", "deception", "complexity", "confusion",
        "pressure", "urgency", "demand"
    ]
    
    # Count positive indicators
    positive_count = sum(1 for indicator in integrity_indicators if indicator in protocol_text)
    
    # Count negative indicators
    negative_count = sum(1 for indicator in misalignment_indicators if indicator in protocol_text)
    
    _dprint(f"  Positive indicators found: {positive_count}")
    _dprint(f"  Negative indicators found: {negative_count}")
    
    # Simple scoring: more positive than negative = aligned
    content_aligned = positive_count >= negative_count
    if not content_aligned:
        reasons.append(f"Content misalignment: {negative_count} negative indicators vs {positive_count} positive")
    
    # Overall alignment requires both structure and content
    aligned = len(reasons) == 0
    
    _dprint(f"[INTEGRITY] Stones check result | id={protocol_id} aligned={aligned}")
    if reasons:
        _dprint("  Stones reasons:\n", pformat(reasons))
    
    return aligned, reasons


def check_coherence(protocol_data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Check if protocol is coherent and well-structured.
    Returns (coherent: bool, reasons: List[str])
    """
    protocol_id = (protocol_data or {}).get("Protocol ID", "<unknown>")
    themes = protocol_data.get("Themes", [])
    
    _dprint(f"[INTEGRITY] Coherence check start  | id={protocol_id}")
    _dprint(f"  Theme count: {len(themes)}")
    
    reasons = []
    
    # Check basic structure
    if not protocol_data.get("Title"):
        reasons.append("Missing Title")
    
    if not protocol_data.get("Overall Purpose"):
        reasons.append("Missing Overall Purpose")
    
    if not protocol_data.get("When To Use This Protocol"):
        reasons.append("Missing When To Use This Protocol")
    
    # Check Themes structure
    if not themes:
        reasons.append("No Themes specified")
    elif len(themes) < 5:
        reasons.append(f"Too few Themes ({len(themes)}). Need at least 5.")
    elif len(themes) > 7:
        reasons.append(f"Too many Themes ({len(themes)}). Maximum is 7.")
    
    # Check each theme for completeness
    for idx, theme in enumerate(themes, start=1):
        name = theme.get("Name", f"Theme {idx}")
        gqs = theme.get("Guiding Questions", [])
        outcomes = theme.get("Outcomes", {})
        
        _dprint(f"   - Theme {idx}: {name} | GQs={len(gqs)} | Outcomes keys={list(outcomes.keys())}")
        
        if not name or name == f"Theme {idx}":
            reasons.append(f"Theme {idx}: Missing or generic name")
        
        if len(gqs) < 3:
            reasons.append(f"Theme {idx} ({name}): Too few guiding questions ({len(gqs)}). Need at least 3.")
        
        if len(gqs) > 5:
            reasons.append(f"Theme {idx} ({name}): Too many guiding questions ({len(gqs)}). Maximum is 5.")
        
        # Check outcomes structure
        required_outcomes = ["Poor", "Expected", "Excellent", "Transcendent"]
        missing_outcomes = [outcome for outcome in required_outcomes if outcome not in outcomes]
        if missing_outcomes:
            reasons.append(f"Theme {idx} ({name}): Missing outcomes: {missing_outcomes}")
        
        # Check for repetitive or shallow outcomes
        for outcome_level, outcome_data in outcomes.items():
            if isinstance(outcome_data, dict):
                # Check if outcomes are too similar (simple heuristic)
                outcome_text = json.dumps(outcome_data, default=str).lower()
                if len(outcome_text) < 50:
                    reasons.append(f"Theme {idx} ({name}): {outcome_level} outcome too shallow (< 50 chars)")
    
    # Check for repetitive themes
    theme_names = [theme.get("Name", "") for theme in themes]
    if len(set(theme_names)) != len(theme_names):
        reasons.append("Duplicate theme names found")
    
    # Check completion prompts
    completion_prompts = protocol_data.get("Completion Prompts", [])
    if not completion_prompts:
        reasons.append("No Completion Prompts specified")
    elif len(completion_prompts) < 2:
        reasons.append(f"Too few completion prompts ({len(completion_prompts)}). Need at least 2.")
    elif len(completion_prompts) > 5:
        reasons.append(f"Too many completion prompts ({len(completion_prompts)}). Maximum is 5.")
    
    coherent = len(reasons) == 0
    
    _dprint(f"[INTEGRITY] Coherence result      | id={protocol_id} coherent={coherent}")
    if reasons:
        _dprint("  Coherence reasons:\n", pformat(reasons))
    
    return coherent, reasons


def run_integrity_gate(protocol_data: Dict[str, Any]) -> IntegrityResult:
    """
    Run protocol through integrity gate checks.
    Includes Stones alignment and coherence checks.
    """
    protocol_id = (protocol_data or {}).get("Protocol ID", "<unknown>")
    _dprint(f"[INTEGRITY] Gate start            | id={protocol_id}")
    
    stones_aligned, stones_reasons = check_stones_alignment(protocol_data)
    coherent, coherence_reasons = check_coherence(protocol_data)
    
    # Both checks must pass
    passed = stones_aligned and coherent
    
    # Combine all reasons
    all_reasons = stones_reasons + coherence_reasons
    
    # Generate notes
    notes = []
    if not stones_aligned:
        notes.append("Protocol does not align with Stones principles")
        notes.extend([f"  - {reason}" for reason in stones_reasons])
    if not coherent:
        notes.append("Protocol lacks coherence or structure")
        notes.extend([f"  - {reason}" for reason in coherence_reasons])
    if passed:
        notes.append("Protocol passed all integrity checks")
    
    _dprint(f"[INTEGRITY] Gate result           | id={protocol_id} passed={passed}")
    if all_reasons:
        _dprint("  Gate reasons:\n", pformat(all_reasons))
    
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
    
    Note: This function maintains backward compatibility by accepting protocol_text,
    but now works with protocol_data from the canon.
    """
    # For backward compatibility, we need to handle both string and dict inputs
    # If it's a string, we can't do detailed integrity checks, so we'll do basic validation
    if isinstance(protocol_text, str):
        protocol_id = "<string-input>"
        _dprint(f"[INTEGRITY] Delivery validation   | id={protocol_id} (string input)")
        
        # Basic string validation
        passed = len(protocol_text) > 50 and "integrity" in protocol_text.lower()
        
        _dprint(f"[INTEGRITY] Delivery result       | id={protocol_id} ok={passed}")
        
        return IntegrityResult(
            passed=passed,
            stones_aligned=passed,
            coherent=passed,
            notes=["String input - limited validation"] if not passed else ["Basic string validation passed"]
        )
    
    # If it's a dict (protocol_data), use full integrity gate
    protocol_id = (protocol_text or {}).get("Protocol ID", "<unknown>")
    _dprint(f"[INTEGRITY] Delivery validation   | id={protocol_id}")
    
    result = run_integrity_gate(protocol_text)
    
    _dprint(f"[INTEGRITY] Delivery result       | id={protocol_id} ok={result.passed}")
    if not result.passed:
        _dprint("  Delivery errors:\n", pformat(result.notes))
    
    return result
