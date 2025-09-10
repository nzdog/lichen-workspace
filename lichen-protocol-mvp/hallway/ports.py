"""
IO interface protocols for dependency inversion.
Defines narrow contracts that adapters must implement.
"""

from typing import Protocol, List, Mapping, Any, Optional, Dict
from datetime import datetime


class LLM(Protocol):
    """Language model interface."""

    async def complete(self, messages: List[Mapping[str, str]], **opts) -> str:
        """Complete a conversation with the given messages."""
        ...


class VectorStore(Protocol):
    """Vector database interface."""

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for the given texts."""
        ...

    async def search(
        self,
        query_vec: List[float],
        k: int,
        filters: Optional[Mapping] = None
    ) -> List[Mapping[str, Any]]:
        """Search for similar vectors."""
        ...


class Storage(Protocol):
    """Persistent storage interface."""

    async def put_json(self, bucket: str, key: str, obj: Any) -> None:
        """Store a JSON object."""
        ...

    async def get_json(self, bucket: str, key: str) -> Any:
        """Retrieve a JSON object."""
        ...

    async def exists(self, bucket: str, key: str) -> bool:
        """Check if an object exists."""
        ...


class Clock(Protocol):
    """Time interface for testability."""

    def now_iso(self) -> str:
        """Get current time in ISO format."""
        ...

    def now_timestamp(self) -> float:
        """Get current timestamp."""
        ...


class IdFactory(Protocol):
    """ID generation interface."""

    def new_id(self, prefix: str = "run") -> str:
        """Generate a new unique ID."""
        ...


class Metrics(Protocol):
    """Metrics collection interface."""

    def incr(self, name: str, **tags) -> None:
        """Increment a counter."""
        ...

    def timing(self, name: str, ms: float, **tags) -> None:
        """Record a timing measurement."""
        ...

    def gauge(self, name: str, value: float, **tags) -> None:
        """Set a gauge value."""
        ...


class Logger(Protocol):
    """Structured logging interface."""

    def info(self, event: Mapping[str, Any]) -> None:
        """Log an info event."""
        ...

    def error(self, event: Mapping[str, Any]) -> None:
        """Log an error event."""
        ...

    def debug(self, event: Mapping[str, Any]) -> None:
        """Log a debug event."""
        ...


class Ports(Protocol):
    """Bundle of all IO interfaces needed by the hallway."""

    llm: LLM
    vec: VectorStore
    store: Storage
    clock: Clock
    ids: IdFactory
    metrics: Metrics
    log: Logger
