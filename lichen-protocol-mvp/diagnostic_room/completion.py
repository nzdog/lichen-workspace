"""
Completion Module
Implements completion marker requirement for Diagnostic Room
"""


def append_fixed_marker(text: str) -> str:
    """
    Appends the fixed completion marker to display_text.
    Single marker only: [[COMPLETE]]
    No variants, no policies, no alternatives.
    """
    return text + " [[COMPLETE]]"
