"""
RAG (Retrieval-Augmented Generation) module.

Provides protocol routing and retrieval capabilities.
"""

from .router import ProtocolRouter, build_protocol_catalog, parse_query, route_query

__all__ = ["ProtocolRouter", "build_protocol_catalog", "parse_query", "route_query"]
