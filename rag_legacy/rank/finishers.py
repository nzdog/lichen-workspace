"""
Ranking and finishing utilities for retrieval results.

Provides MMR (Maximal Marginal Relevance) reranking with guardrails and
optional cross-encoder reranking capabilities.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    """Represents a retrieval candidate with score and metadata."""
    id: str
    score: float
    text: str
    metadata: Dict[str, Any] = None


@dataclass
class MMRConfig:
    """Configuration for MMR reranking."""
    lambda_param: float = 0.5  # Balance between relevance and diversity
    max_candidates: int = 200  # Maximum candidates to process
    batch_size: int = 50  # Batch size for similarity computation


def mmr_rerank(candidates: List[Dict[str, Any]], query_embedding: np.ndarray, 
               candidate_embeddings: np.ndarray, top_k: int, 
               config: MMRConfig = None) -> List[Dict[str, Any]]:
    """
    Rerank candidates using Maximal Marginal Relevance (MMR).
    
    Args:
        candidates: List of candidate dictionaries with 'id', 'score', 'text'
        query_embedding: Query embedding vector
        candidate_embeddings: Array of candidate embeddings
        top_k: Number of final results to return
        config: MMR configuration
        
    Returns:
        List of reranked candidates
    """
    if config is None:
        config = MMRConfig()
    
    # Guardrails: handle empty or insufficient candidates
    if not candidates:
        logger.warning("MMR: No candidates provided")
        return []
    
    if len(candidates) == 0:
        logger.warning("MMR: Empty candidates list")
        return []
    
    # Guardrails: limit candidates to prevent excessive computation
    if len(candidates) > config.max_candidates:
        logger.info(f"MMR: Limiting candidates from {len(candidates)} to {config.max_candidates}")
        candidates = candidates[:config.max_candidates]
        candidate_embeddings = candidate_embeddings[:config.max_candidates]
    
    # Guardrails: ensure embeddings match candidates
    if len(candidates) != len(candidate_embeddings):
        logger.error(f"MMR: Candidates count ({len(candidates)}) != embeddings count ({len(candidate_embeddings)})")
        # Truncate to minimum length
        min_len = min(len(candidates), len(candidate_embeddings))
        candidates = candidates[:min_len]
        candidate_embeddings = candidate_embeddings[:min_len]
        logger.warning(f"MMR: Truncated to {min_len} candidates")
    
    # Guardrails: limit top_k to available candidates
    top_k = min(top_k, len(candidates))
    
    try:
        # Create candidate mapping
        candidate_map = {}
        for i, candidate in enumerate(candidates):
            candidate_id = candidate.get('id', str(i))
            candidate_map[candidate_id] = {
                'index': i,
                'score': candidate.get('score', 0.0),
                'text': candidate.get('text', ''),
                'metadata': candidate.get('metadata', {})
            }
        
        # Initialize MMR selection
        selected_indices = []
        remaining_indices = list(range(len(candidates)))
        
        # First selection: highest relevance
        if remaining_indices:
            # Use original scores for first selection
            first_idx = max(remaining_indices, key=lambda i: candidates[i].get('score', 0.0))
            selected_indices.append(first_idx)
            remaining_indices.remove(first_idx)
        
        # Subsequent selections: MMR
        while len(selected_indices) < top_k and remaining_indices:
            best_idx = None
            best_mmr_score = float('-inf')
            
            # Limit scan to prevent excessive computation
            scan_indices = remaining_indices[:config.max_candidates]
            
            for idx in scan_indices:
                # Relevance: cosine similarity to query
                relevance = _cosine_similarity(query_embedding, candidate_embeddings[idx])
                
                # Diversity: max similarity to already selected
                diversity = 0.0
                if selected_indices:
                    similarities = [_cosine_similarity(candidate_embeddings[idx], candidate_embeddings[sel_idx]) 
                                  for sel_idx in selected_indices]
                    diversity = max(similarities) if similarities else 0.0
                
                # MMR score
                mmr_score = config.lambda_param * relevance - (1 - config.lambda_param) * diversity
                
                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_idx = idx
            
            if best_idx is not None:
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)
            else:
                break
        
        # Return reranked candidates
        reranked = []
        for idx in selected_indices:
            if 0 <= idx < len(candidates):
                reranked.append(candidates[idx])
        
        logger.info(f"MMR reranked {len(candidates)} candidates to {len(reranked)}")
        return reranked
        
    except Exception as e:
        logger.error(f"MMR reranking failed: {e}")
        # Fallback: return top candidates by original score
        sorted_candidates = sorted(candidates, key=lambda x: x.get('score', 0.0), reverse=True)
        return sorted_candidates[:top_k]


def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    try:
        # Ensure vectors are normalized
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return np.dot(vec1, vec2) / (norm1 * norm2)
    except Exception as e:
        logger.warning(f"Cosine similarity computation failed: {e}")
        return 0.0


def cross_encoder_rerank(candidates: List[Dict[str, Any]], query: str, 
                        cross_encoder_model, top_k: int) -> List[Dict[str, Any]]:
    """
    Rerank candidates using cross-encoder model.
    
    Args:
        candidates: List of candidate dictionaries
        query: Query text
        cross_encoder_model: Cross-encoder model
        top_k: Number of final results to return
        
    Returns:
        List of reranked candidates
    """
    if not candidates:
        return []
    
    if cross_encoder_model is None:
        logger.warning("Cross-encoder model not available, returning original candidates")
        return candidates[:top_k]
    
    try:
        # Prepare query-document pairs
        pairs = []
        for candidate in candidates:
            text = candidate.get('text', '')
            pairs.append([query, text])
        
        # Get cross-encoder scores
        scores = cross_encoder_model.predict(pairs)
        
        # Combine with original scores and rerank
        reranked = []
        for i, candidate in enumerate(candidates):
            new_candidate = candidate.copy()
            new_candidate['cross_encoder_score'] = float(scores[i])
            # Combine with original score (weighted average)
            original_score = candidate.get('score', 0.0)
            combined_score = 0.7 * float(scores[i]) + 0.3 * original_score
            new_candidate['score'] = combined_score
            reranked.append(new_candidate)
        
        # Sort by combined score
        reranked.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"Cross-encoder reranked {len(candidates)} candidates to {top_k}")
        return reranked[:top_k]
        
    except Exception as e:
        logger.error(f"Cross-encoder reranking failed: {e}")
        # Fallback: return original candidates
        return candidates[:top_k]


def apply_fast_finisher(candidates: List[Dict[str, Any]], query_embedding: np.ndarray,
                       candidate_embeddings: np.ndarray, top_k: int = 8) -> List[Dict[str, Any]]:
    """
    Apply fast lane finisher: MMR reranking.
    
    Args:
        candidates: List of candidates
        query_embedding: Query embedding
        candidate_embeddings: Candidate embeddings
        top_k: Number of results to return
        
    Returns:
        List of final candidates
    """
    config = MMRConfig(lambda_param=0.5, max_candidates=200)
    return mmr_rerank(candidates, query_embedding, candidate_embeddings, top_k, config)


def apply_accurate_finisher(candidates: List[Dict[str, Any]], query: str,
                           query_embedding: np.ndarray, candidate_embeddings: np.ndarray,
                           cross_encoder_model=None, top_k: int = 8) -> List[Dict[str, Any]]:
    """
    Apply accurate lane finisher: MMR + optional cross-encoder reranking.
    
    Args:
        candidates: List of candidates
        query: Query text
        query_embedding: Query embedding
        candidate_embeddings: Candidate embeddings
        cross_encoder_model: Optional cross-encoder model
        top_k: Number of final results to return
        
    Returns:
        List of final candidates
    """
    # First apply MMR
    config = MMRConfig(lambda_param=0.6, max_candidates=200)
    mmr_candidates = mmr_rerank(candidates, query_embedding, candidate_embeddings, 
                               min(top_k * 3, len(candidates)), config)
    
    # Then apply cross-encoder if available
    if cross_encoder_model and len(mmr_candidates) > top_k:
        return cross_encoder_rerank(mmr_candidates, query, cross_encoder_model, top_k)
    
    return mmr_candidates[:top_k]


def validate_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate and clean candidate list.
    
    Args:
        candidates: List of candidate dictionaries
        
    Returns:
        Cleaned list of candidates
    """
    if not candidates:
        return []
    
    cleaned = []
    for i, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            logger.warning(f"Skipping non-dict candidate at index {i}")
            continue
        
        # Ensure required fields
        if 'id' not in candidate:
            candidate['id'] = f"candidate_{i}"
        
        if 'score' not in candidate:
            candidate['score'] = 0.0
        
        if 'text' not in candidate:
            candidate['text'] = ""
        
        if 'metadata' not in candidate:
            candidate['metadata'] = {}
        
        cleaned.append(candidate)
    
    return cleaned


def deduplicate_candidates(candidates: List[Dict[str, Any]], 
                          key_field: str = 'id') -> List[Dict[str, Any]]:
    """
    Remove duplicate candidates based on key field.
    
    Args:
        candidates: List of candidates
        key_field: Field to use for deduplication
        
    Returns:
        Deduplicated list of candidates
    """
    seen = set()
    deduplicated = []
    
    for candidate in candidates:
        key = candidate.get(key_field, '')
        if key not in seen:
            seen.add(key)
            deduplicated.append(candidate)
    
    logger.info(f"Deduplicated {len(candidates)} candidates to {len(deduplicated)}")
    return deduplicated
