"""
Depth Module
Implements Depth Selection theme from Protocol Room Protocol
"""

from typing import Optional
from .room_types import ProtocolDepth


def select_protocol_depth(
    requested_depth: Optional[ProtocolDepth] = None,
    readiness_level: Optional[str] = None,
    time_available: Optional[int] = None
) -> ProtocolDepth:
    """
    Deterministic depth selection logic.
    No AI, no heuristics, no smart selection beyond deterministic rules.
    """
    
    # If explicit depth is requested, respect it
    if requested_depth and requested_depth in ["full", "theme", "scenario"]:
        return requested_depth
    
    # Deterministic rules based on readiness level
    if readiness_level == "HOLD":
        return "scenario"  # Light entry for holding states
    elif readiness_level == "LATER":
        return "theme"     # Medium depth for later states
    elif readiness_level == "SOFT_HOLD":
        return "theme"     # Medium depth for soft holds
    
    # Deterministic rules based on time available
    if time_available is not None:
        if time_available < 5:
            return "scenario"
        elif time_available < 15:
            return "theme"
        else:
            return "full"
    
    # Default: full protocol
    return "full"


def format_depth_label(depth: ProtocolDepth) -> str:
    """
    Format depth label for display.
    Deterministic formatting only.
    """
    if depth == "full":
        return "Full Protocol"
    elif depth == "theme":
        return "Theme Summary"
    elif depth == "scenario":
        return "Scenario Entry"
    else:
        return "Protocol"


def get_depth_description(depth: ProtocolDepth) -> str:
    """
    Get description of what each depth provides.
    Deterministic descriptions only.
    """
    if depth == "full":
        return "Complete protocol with all steps, details, and guidance"
    elif depth == "theme":
        return "Core theme and purpose without detailed steps"
    elif depth == "scenario":
        return "Quick entry point for immediate application"
    else:
        return "Protocol guidance"
