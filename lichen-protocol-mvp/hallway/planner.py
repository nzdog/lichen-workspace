"""
Pure room planning function for the Hallway Protocol.
"""

from typing import List


def plan_rooms(sequence: List[str], subset: List[str] | None, mini_walk: bool) -> List[str]:
    """
    Return the ordered list of rooms to run.

    Semantics:
      - If subset is provided, preserve original order and include only those rooms (mini_walk is ignored).
      - Else if mini_walk is True, return the first three rooms (sequence[:3]) or fewer if sequence is shorter.
      - Else return the full sequence.
    """
    if subset:
        allowed = set(subset)
        return [r for r in sequence if r in allowed]
    return sequence[:3] if mini_walk else list(sequence)
