"""
Mock implementations for testing and development.
"""

import time
import uuid
from datetime import datetime
from typing import List, Mapping, Any, Optional

from ..ports import LLM, VectorStore, Clock, IdFactory, Metrics, Logger


class MockLLM(LLM):
    """Mock LLM for testing."""

    def __init__(self, responses: Optional[List[str]] = None):
        self.responses = responses or ["mock response"]
        self.call_count = 0

    async def complete(self, messages: List[Mapping[str, str]], **opts) -> str:
        """Return a predetermined response."""
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response


class MockVectorStore(VectorStore):
    """Mock vector store for testing."""

    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self.embeddings = []
        self.search_results = []

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Return deterministic embeddings."""
        embeddings = []
        for i, text in enumerate(texts):
            # Simple hash-based embedding for deterministic tests
            embedding = [hash(text + str(j)) % 1000 / 1000.0 for j in range(self.embedding_dim)]
            embeddings.append(embedding)
        return embeddings

    async def search(
        self,
        query_vec: List[float],
        k: int,
        filters: Optional[Mapping] = None
    ) -> List[Mapping[str, Any]]:
        """Return predetermined search results."""
        return self.search_results[:k]


class MockClock(Clock):
    """Mock clock for testing."""

    def __init__(self, fixed_time: Optional[float] = None):
        self._fixed_time = fixed_time

    def now_iso(self) -> str:
        """Return current time in ISO format."""
        timestamp = self._fixed_time if self._fixed_time else time.time()
        return datetime.fromtimestamp(timestamp).isoformat()

    def now_timestamp(self) -> float:
        """Return current timestamp."""
        return self._fixed_time if self._fixed_time else time.time()


class MockIdFactory(IdFactory):
    """Mock ID factory for testing."""

    def __init__(self, deterministic: bool = True):
        self.deterministic = deterministic
        self.counter = 0

    def new_id(self, prefix: str = "run") -> str:
        """Generate a new ID."""
        if self.deterministic:
            self.counter += 1
            return f"{prefix}-{self.counter:04d}"
        else:
            return f"{prefix}-{uuid.uuid4().hex[:8]}"


class MockMetrics(Metrics):
    """Mock metrics collector for testing."""

    def __init__(self):
        self.counters = {}
        self.timings = {}
        self.gauges = {}

    def incr(self, name: str, **tags) -> None:
        """Increment a counter."""
        key = (name, tuple(sorted(tags.items())))
        self.counters[key] = self.counters.get(key, 0) + 1

    def timing(self, name: str, ms: float, **tags) -> None:
        """Record a timing measurement."""
        key = (name, tuple(sorted(tags.items())))
        if key not in self.timings:
            self.timings[key] = []
        self.timings[key].append(ms)

    def gauge(self, name: str, value: float, **tags) -> None:
        """Set a gauge value."""
        key = (name, tuple(sorted(tags.items())))
        self.gauges[key] = value


class MockLogger(Logger):
    """Mock logger for testing."""

    def __init__(self):
        self.events = []

    def info(self, event: Mapping[str, Any]) -> None:
        """Log an info event."""
        self.events.append(("INFO", dict(event)))

    def error(self, event: Mapping[str, Any]) -> None:
        """Log an error event."""
        self.events.append(("ERROR", dict(event)))

    def debug(self, event: Mapping[str, Any]) -> None:
        """Log a debug event."""
        self.events.append(("DEBUG", dict(event)))
