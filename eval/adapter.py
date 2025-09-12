"""
Adapter layer for integrating with actual RAG system components.
This module provides the interface between the evaluation harness and the live system.
"""

import json
import os
import time
from functools import lru_cache
from typing import List, Dict, Any, Optional


@lru_cache(maxsize=1)
def _load_dummy_retrieval_data() -> Dict[str, List[Dict[str, Any]]]:
    """Load dummy retrieval data from JSONL file with caching."""
    retrieval_file = "data/dummy_retrieval.jsonl"
    if not os.path.exists(retrieval_file):
        return {}
    
    data = {}
    with open(retrieval_file, 'r') as f:
        for line in f:
            entry = json.loads(line.strip())
            query = entry["query"]
            if query not in data:
                data[query] = []
            data[query].append(entry)
    
    return data


@lru_cache(maxsize=1)
def _load_dummy_answers_data() -> Dict[str, List[Dict[str, Any]]]:
    """Load dummy answers data from JSONL file with caching."""
    answers_file = "data/dummy_answers.jsonl"
    if not os.path.exists(answers_file):
        return {}
    
    data = {}
    with open(answers_file, 'r') as f:
        for line in f:
            entry = json.loads(line.strip())
            query = entry["query"]
            if query not in data:
                data[query] = []
            data[query].append(entry)
    
    return data


def retrieve(query: str, lane: str) -> List[Dict[str, Any]]:
    """
    Retrieve documents for a query using the specified lane.
    
    Args:
        query: The search query
        lane: The lane to use ("fast" or "accurate")
        
    Returns:
        List of at least 20 dictionaries, each containing:
        - doc (str): Document identifier
        - chunk (int): Chunk number within the document
        - rank (int): 1-based ranking position
        - score (float): Relevance score
        - text (str): The actual text content
    """
    # Use the RAG adapter from lichen-protocol-mvp
    try:
        import sys
        sys.path.append('lichen-protocol-mvp')
        from hallway.adapters.rag_adapter import get_rag_adapter
        
        rag_adapter = get_rag_adapter()
        return rag_adapter.retrieve(query, lane)
    except ImportError:
        # Fallback to dummy mode if RAG adapter not available
        if os.getenv("USE_DUMMY_RAG") == "1":
            return _retrieve_dummy(query, lane)
        else:
            raise NotImplementedError(
                "RAG adapter not available. Set USE_DUMMY_RAG=1 for the dummy retriever.\n"
                "TODO: Ensure lichen-protocol-mvp is in the Python path."
            )


def _retrieve_dummy(query: str, lane: str) -> List[Dict[str, Any]]:
    """Retrieve documents using dummy data from JSONL files."""
    retrieval_data = _load_dummy_retrieval_data()
    
    if query not in retrieval_data:
        return []
    
    # Find matching entry for this query and lane
    matching_entries = []
    for entry in retrieval_data[query]:
        entry_lane = entry.get("lane", "both")
        if entry_lane == "both" or entry_lane == lane:
            matching_entries.append(entry)
    
    if not matching_entries:
        return []
    
    # Use the first matching entry (prefer exact lane match if available)
    entry = matching_entries[0]
    return entry.get("results", [])


def generate(query: str, context_texts: List[str], lane: str) -> Dict[str, Any]:
    """
    Generate an answer using the AI Room model with constrained context.
    
    Args:
        query: The user query
        context_texts: List of context texts to use for generation
        lane: The lane to use ("fast" or "accurate")
        
    Returns:
        Dictionary containing:
        - answer (str): The generated answer
        - hallucinations (int): Count of hallucinated facts (0 for now)
    """
    # Use the RAG adapter from lichen-protocol-mvp
    try:
        import sys
        sys.path.append('lichen-protocol-mvp')
        from hallway.adapters.rag_adapter import get_rag_adapter
        
        rag_adapter = get_rag_adapter()
        return rag_adapter.generate(query, context_texts, lane)
    except ImportError:
        # Fallback to dummy mode if RAG adapter not available
        if os.getenv("USE_DUMMY_RAG") == "1":
            return _generate_dummy(query, context_texts, lane)
        else:
            raise NotImplementedError(
                "RAG adapter not available. Set USE_DUMMY_RAG=1 for the dummy generator.\n"
                "TODO: Ensure lichen-protocol-mvp is in the Python path."
            )


def _generate_dummy(query: str, context_texts: List[str], lane: str) -> Dict[str, Any]:
    """Generate answer using dummy data or synthesize from context."""
    answers_data = _load_dummy_answers_data()
    
    # Look for pre-written answer for this query and lane
    if query in answers_data:
        for entry in answers_data[query]:
            entry_lane = entry.get("lane", "both")
            if entry_lane == "both" or entry_lane == lane:
                return {
                    "answer": entry["answer"],
                    "hallucinations": entry.get("hallucinations", 0)
                }
    
    # If no pre-written answer, synthesize from context
    if not context_texts:
        return {
            "answer": f"I don't have enough context to answer the query: {query}",
            "hallucinations": 0
        }
    
    # Use top 2-3 context texts to build answer
    top_contexts = context_texts[:3]
    context_summary = ". ".join(top_contexts)
    
    # Truncate if too long
    if len(context_summary) > 500:
        context_summary = context_summary[:500] + "..."
    
    if lane == "fast":
        # Fast lane generates shorter, more direct answers
        answer = f"Based on the available context, the key insights for {query.lower()} are: {context_summary[:300]}"
    else:  # accurate
        # Accurate lane generates more comprehensive answers
        answer = f"In response to your question about {query.lower()}, the comprehensive analysis shows: {context_summary[:400]} This approach emphasizes sustainable leadership practices and maintaining team integrity."
    
    return {
        "answer": answer,
        "hallucinations": 0
    }


def expected_stones_for_query(query: str) -> List[str]:
    """
    Get expected Stones slugs/names for a query.
    
    Args:
        query: The user query
        
    Returns:
        List of expected stone identifiers, or empty list if unknown
    """
    # TODO: Replace with actual Stones lookup logic
    # This should return the expected stone slugs/names based on query analysis
    # For now, return empty list - the harness will rely on expected_stones from the evalset
    
    # In dummy mode, we rely on the expected_stones field in the evalset
    # TODO: Implement heuristic-based stone mapping for queries without explicit expected_stones
    return []
