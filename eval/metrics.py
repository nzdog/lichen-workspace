"""
Metrics implementation for RAG evaluation harness.
"""

import math
from typing import List, Set, Dict, Any


def precision_at_k(ranked_doc_ids: List[str], gold_doc_ids: Set[str], k: int) -> float:
    """
    Calculate precision at k.
    
    Args:
        ranked_doc_ids: List of document IDs ranked by relevance
        gold_doc_ids: Set of relevant document IDs
        k: Number of top documents to consider
        
    Returns:
        Fraction of top-k documents that are relevant
    """
    if k <= 0:
        return 0.0
    
    top_k = ranked_doc_ids[:k]
    if len(top_k) == 0:
        return 0.0
    relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in gold_doc_ids)
    return relevant_in_top_k / len(top_k)


def recall_at_k(ranked_doc_ids: List[str], gold_doc_ids: Set[str], k: int) -> float:
    """
    Calculate recall at k.
    
    Args:
        ranked_doc_ids: List of document IDs ranked by relevance
        gold_doc_ids: Set of relevant document IDs
        k: Number of top documents to consider
        
    Returns:
        Fraction of relevant documents found in top-k (0 if gold set is empty)
    """
    if not gold_doc_ids:
        return 0.0
    
    top_k = ranked_doc_ids[:k]
    relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in gold_doc_ids)
    return relevant_in_top_k / len(gold_doc_ids)


def rr_at_k(ranked_doc_ids: List[str], gold_doc_ids: Set[str], k: int) -> float:
    """
    Calculate reciprocal rank at k.
    
    Args:
        ranked_doc_ids: List of document IDs ranked by relevance
        gold_doc_ids: Set of relevant document IDs
        k: Number of top documents to consider
        
    Returns:
        Reciprocal rank of first relevant document within top-k; 0 if none found
    """
    if k <= 0:
        return 0.0
    
    top_k = ranked_doc_ids[:k]
    for i, doc_id in enumerate(top_k):
        if doc_id in gold_doc_ids:
            return 1.0 / (i + 1)  # 1-based rank
    
    return 0.0


def mrr_at_k(batches: List[List[str]], gold_sets: List[Set[str]], k: int) -> float:
    """
    Calculate mean reciprocal rank at k across multiple queries.
    
    Args:
        batches: List of ranked document ID lists (one per query)
        gold_sets: List of relevant document ID sets (one per query)
        k: Number of top documents to consider
        
    Returns:
        Mean reciprocal rank across all queries
    """
    if not batches or not gold_sets or len(batches) != len(gold_sets):
        return 0.0
    
    reciprocal_ranks = [rr_at_k(ranked_docs, gold_docs, k) 
                       for ranked_docs, gold_docs in zip(batches, gold_sets)]
    return sum(reciprocal_ranks) / len(reciprocal_ranks)


def dcg_at_k(ranked_doc_ids: List[str], gold_doc_ids: Set[str], k: int) -> float:
    """
    Calculate discounted cumulative gain at k.
    
    Args:
        ranked_doc_ids: List of document IDs ranked by relevance
        gold_doc_ids: Set of relevant document IDs
        k: Number of top documents to consider
        
    Returns:
        DCG value
    """
    if k <= 0:
        return 0.0
    
    top_k = ranked_doc_ids[:k]
    dcg = 0.0
    
    for i, doc_id in enumerate(top_k):
        relevance = 1.0 if doc_id in gold_doc_ids else 0.0
        if i == 0:
            dcg += relevance
        else:
            dcg += relevance / math.log2(i + 1)
    
    return dcg


def idcg_at_k(gold_doc_ids: Set[str], k: int) -> float:
    """
    Calculate ideal DCG at k (perfect ranking).
    
    Args:
        gold_doc_ids: Set of relevant document IDs
        k: Number of top documents to consider
        
    Returns:
        Ideal DCG value
    """
    if k <= 0 or not gold_doc_ids:
        return 0.0
    
    # For binary relevance, ideal DCG is just the sum of 1/log2(i+1) for i=0 to min(k-1, |gold|-1)
    num_relevant = min(k, len(gold_doc_ids))
    idcg = 0.0
    
    for i in range(num_relevant):
        if i == 0:
            idcg += 1.0
        else:
            idcg += 1.0 / math.log2(i + 1)
    
    return idcg


def ndcg_at_k(ranked_doc_ids: List[str], gold_doc_ids: Set[str], k: int) -> float:
    """
    Calculate normalized discounted cumulative gain at k.
    
    Args:
        ranked_doc_ids: List of document IDs ranked by relevance
        gold_doc_ids: Set of relevant document IDs
        k: Number of top documents to consider
        
    Returns:
        nDCG value (0-1 scale)
    """
    if k <= 0:
        return 0.0
    
    dcg = dcg_at_k(ranked_doc_ids, gold_doc_ids, k)
    idcg = idcg_at_k(gold_doc_ids, k)
    
    if idcg == 0:
        return 0.0
    
    return dcg / idcg


def diversity_unique_docs_topk(ranked_pairs: List[Dict[str, Any]], k: int) -> int:
    """
    Count unique documents in top-k results.
    
    Args:
        ranked_pairs: List of dictionaries containing document information
        k: Number of top results to consider
        
    Returns:
        Number of unique documents in top-k
    """
    if k <= 0 or not ranked_pairs:
        return 0
    
    top_k = ranked_pairs[:k]
    unique_docs = set()
    
    for pair in top_k:
        if "doc" in pair:
            unique_docs.add(pair["doc"])
    
    return len(unique_docs)


def p95(values: List[float]) -> float:
    """
    Calculate 95th percentile.
    
    Args:
        values: List of numeric values
        
    Returns:
        95th percentile value
    """
    if not values:
        return 0.0
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    index = math.ceil(0.95 * n) - 1  # Convert to 0-based index
    index = min(index, n - 1)  # Ensure we don't go out of bounds
    
    return sorted_values[index]


def simple_grounding_score(answer_text: str, support_texts: List[str]) -> float:
    """
    Simple token-overlap heuristic for grounding score (1-5 scale).
    
    Args:
        answer_text: The generated answer text
        support_texts: List of supporting context texts
        
    Returns:
        Grounding score between 1.0 and 5.0
    """
    if not answer_text or not support_texts:
        return 1.0
    
    # Simple token-based overlap calculation
    answer_tokens = set(answer_text.lower().split())
    total_overlap = 0
    total_context_tokens = 0
    
    for support_text in support_texts:
        if not support_text:
            continue
        
        context_tokens = set(support_text.lower().split())
        overlap = len(answer_tokens & context_tokens)
        
        total_overlap += overlap
        total_context_tokens += len(context_tokens)
    
    if total_context_tokens == 0:
        return 1.0
    
    # Calculate overlap ratio
    overlap_ratio = total_overlap / total_context_tokens
    
    # Map to 1-5 scale
    # 0% overlap -> 1.0, 100% overlap -> 5.0
    score = 1.0 + (overlap_ratio * 4.0)
    return min(5.0, max(1.0, score))


def stones_alignment_score(expected_stones: List[str], answer_text: str) -> float:
    """
    Calculate Stones alignment score based on expected stone mentions.
    
    Args:
        expected_stones: List of expected stone slugs/names
        answer_text: The generated answer text
        
    Returns:
        Alignment score between 0.0 and 1.0
    """
    if not expected_stones or not answer_text:
        return 0.0
    
    answer_lower = answer_text.lower()
    found_stones = 0
    
    for stone in expected_stones:
        if not stone:
            continue
        
        # Check if stone name appears in answer (case-insensitive)
        stone_lower = stone.lower()
        # Check for exact matches and partial matches
        # For hyphenated slugs, also check individual words
        words_to_check = stone_lower.split() + stone_lower.split('-')
        words_to_check = [w for w in words_to_check if w]  # Remove empty strings
        
        if (stone_lower in answer_lower or 
            any(word in answer_lower for word in words_to_check)):
            found_stones += 1
    
    return found_stones / len(expected_stones)
