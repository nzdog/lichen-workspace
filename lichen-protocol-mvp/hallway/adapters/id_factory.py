"""
Real ID factory implementation using UUID.
"""

import uuid
from typing import Final
from ..ports import IdFactory


class UuidFactory(IdFactory):
    """Production ID factory using UUID4."""

    _LEN: Final[int] = 12

    def new_id(self, prefix: str = "run") -> str:
        """Generate a new unique ID with the given prefix."""
        return f"{prefix}_{uuid.uuid4().hex[:self._LEN]}"
