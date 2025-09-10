"""
Builder for assembling ports from configuration.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional

from ..ports import Ports
from .mock_adapters import (
    MockLLM, MockVectorStore, MockClock,
    MockIdFactory, MockMetrics, MockLogger
)
from .fs_storage import FilesystemStorage


@dataclass
class PortsImpl:
    """Concrete implementation of the Ports protocol."""
    llm: Any
    vec: Any
    store: Any
    clock: Any
    ids: Any
    metrics: Any
    log: Any


def build_ports(config: Optional[Dict[str, Any]] = None) -> Ports:
    """
    Build a complete Ports bundle from configuration.

    Args:
        config: Configuration dictionary. If None, uses safe defaults.

    Returns:
        Ports implementation
    """
    if not config:
        # Safe defaults for development (no external dependencies)
        logger = MockLogger()
        logger.info({
            "event": "adapter_selection",
            "adapters": {
                "llm": "mock",
                "vec": "mock",
                "store": "filesystem",
                "clock": "mock",
                "ids": "uuid",
                "metrics": "mock",
                "log": "mock"
            }
        })

        return PortsImpl(
            llm=MockLLM(),
            vec=MockVectorStore(),
            store=FilesystemStorage("/tmp/hallway_storage"),
            clock=MockClock(),
            ids=_build_id_factory({"provider": "uuid"}),
            metrics=MockMetrics(),
            log=logger
        )

    # Build real implementations based on config
    # This would be expanded to support OpenAI, Pinecone, etc.
    llm = _build_llm(config.get("llm", {}))
    vec = _build_vector_store(config.get("vector", {}))
    store = _build_storage(config.get("storage", {}))
    clock = _build_clock(config.get("clock", {}))
    ids = _build_id_factory(config.get("ids", {}))
    metrics = _build_metrics(config.get("metrics", {}))
    log = _build_logger(config.get("logging", {}))

    return PortsImpl(
        llm=llm,
        vec=vec,
        store=store,
        clock=clock,
        ids=ids,
        metrics=metrics,
        log=log
    )


def _build_llm(config: Dict[str, Any]):
    """Build LLM implementation from config."""
    provider = config.get("provider", "mock")

    if provider == "mock":
        return MockLLM(config.get("responses"))
    else:
        # Would add OpenAI, Anthropic, etc. here
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _build_vector_store(config: Dict[str, Any]):
    """Build vector store implementation from config."""
    provider = config.get("provider", "mock")

    if provider == "mock":
        return MockVectorStore(config.get("embedding_dim", 384))
    else:
        # Would add Pinecone, FAISS, etc. here
        raise ValueError(f"Unsupported vector store provider: {provider}")


def _build_storage(config: Dict[str, Any]):
    """Build storage implementation from config."""
    provider = config.get("provider", "filesystem")

    if provider == "filesystem":
        base_path = config.get("base_path", "/tmp/hallway_storage")
        return FilesystemStorage(base_path)
    else:
        # Would add S3, GCS, etc. here
        raise ValueError(f"Unsupported storage provider: {provider}")


def _build_clock(config: Dict[str, Any]):
    """Build clock implementation from config."""
    return MockClock(config.get("fixed_time"))


def _build_id_factory(config: Dict[str, Any]):
    """Build ID factory implementation from config."""
    provider = config.get("provider", "uuid")

    if provider == "uuid":
        from .id_factory import UuidFactory
        return UuidFactory()
    elif provider == "mock":
        return MockIdFactory(config.get("deterministic", True))
    else:
        raise ValueError(f"Unsupported ID factory provider: {provider}")


def _build_metrics(config: Dict[str, Any]):
    """Build metrics implementation from config."""
    return MockMetrics()


def _build_logger(config: Dict[str, Any]):
    """Build logger implementation from config."""
    return MockLogger()
