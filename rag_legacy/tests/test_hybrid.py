#!/usr/bin/env python3
"""
Test script for hybrid retriever.
"""

import os
import sys

# Set environment variables
os.environ['FAST_INDEX_PATH'] = 'data/indexes/vecs_fast.faiss'
os.environ['FAST_STATS_PATH'] = 'data/indexes/vecs_fast.stats.json'
os.environ['FAST_META_PATH'] = 'data/indexes/vecs_fast.stats.meta.jsonl'
os.environ['ACCURATE_INDEX_PATH'] = 'data/indexes/vecs_accurate.faiss'
os.environ['ACCURATE_STATS_PATH'] = 'data/indexes/vecs_accurate.stats.json'
os.environ['ACCURATE_META_PATH'] = 'data/indexes/vecs_accurate.stats.meta.jsonl'
os.environ['PROTOCOL_CATALOG_PATH'] = 'data/protocol_catalog.json'
os.environ['RAG_STRATEGY'] = 'protocol_first_hybrid'
os.environ['ROUTER_HARD_GATE'] = '0'

from rag.retrieve.protocol_first_hybrid import ProtocolFirstHybridRetriever

config = {}
retriever = ProtocolFirstHybridRetriever(config)
print('✅ Hybrid retriever initialized successfully')
print('Info:', retriever.get_info())

# Test fast retrieval
results = retriever.retrieve_fast('How do I handle team conflicts?')
print(f'Fast retrieval: {len(results)} results')
for i, result in enumerate(results[:3]):
    print(f'  {i+1}. {result.get("id", "unknown")} (score: {result.get("score", 0):.3f})')
