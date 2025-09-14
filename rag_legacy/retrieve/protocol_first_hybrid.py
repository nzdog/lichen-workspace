"""
Protocol-first hybrid retrieval strategy.

Implements soft-routed hybrid retrieval combining dense vectors, BM25, and protocol catalog
with configurable boosting and finishing strategies.
"""

import os
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import math

# Add rag module to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rag.models import get_embedder, get_cross_encoder
from rag.index.faiss_store import load_faiss_index
from rag.rank.finishers import apply_fast_finisher, apply_accurate_finisher

logger = logging.getLogger(__name__)


class ProtocolFirstHybridRetriever:
    """Hybrid retriever with protocol-first strategy and configurable boosting."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize hybrid retriever.
        
        Args:
            config: Configuration dictionary with paths and parameters
        """
        self.config = config
        
        # Load FAISS indices
        self.fast_index = None
        self.accurate_index = None
        
        # Load protocol catalog
        self.protocol_catalog = None
        
        # Load embedding models
        self.fast_embedder = None
        self.accurate_embedder = None
        self.cross_encoder = None
        
        # Configuration parameters
        self.k_dense = int(os.getenv('K_DENSE', config.get('k_dense', 200)))
        self.k_lex = int(os.getenv('K_LEX', config.get('k_lex', 200)))
        self.rrf_c = int(os.getenv('RRF_C', config.get('rrf_c', 60)))
        self.protocol_topn = int(os.getenv('PROTOCOL_TOPN', config.get('protocol_topn', 10)))
        self.protocol_boost = float(os.getenv('PROTOCOL_BOOST', config.get('protocol_boost', 0.15)))
        self.stone_boost = float(os.getenv('STONE_BOOST', config.get('stone_boost', 0.05)))
        self.fast_return = int(os.getenv('FAST_RETURN', config.get('fast_return', 8)))
        self.accurate_in = int(os.getenv('ACCURATE_IN', config.get('accurate_in', 60)))
        self.accurate_out = int(os.getenv('ACCURATE_OUT', config.get('accurate_out', 8)))
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all retrieval components."""
        try:
            # Load FAISS indices
            fast_index_path = os.getenv('FAST_INDEX_PATH', self.config.get('fast_index_path'))
            fast_stats_path = os.getenv('FAST_STATS_PATH', self.config.get('fast_stats_path'))
            fast_meta_path = os.getenv('FAST_META_PATH', self.config.get('fast_meta_path'))
            
            if fast_index_path and fast_stats_path:
                self.fast_index = load_faiss_index(fast_index_path, fast_stats_path, fast_meta_path)
                logger.info(f"Loaded fast index: {fast_index_path}")
            
            accurate_index_path = os.getenv('ACCURATE_INDEX_PATH', self.config.get('accurate_index_path'))
            accurate_stats_path = os.getenv('ACCURATE_STATS_PATH', self.config.get('accurate_stats_path'))
            accurate_meta_path = os.getenv('ACCURATE_META_PATH', self.config.get('accurate_meta_path'))
            
            if accurate_index_path and accurate_stats_path:
                self.accurate_index = load_faiss_index(accurate_index_path, accurate_stats_path, accurate_meta_path)
                logger.info(f"Loaded accurate index: {accurate_index_path}")
            
            # Load protocol catalog
            catalog_path = os.getenv('PROTOCOL_CATALOG_PATH', self.config.get('protocol_catalog_path'))
            if catalog_path and Path(catalog_path).exists():
                with open(catalog_path, 'r', encoding='utf-8') as f:
                    self.protocol_catalog = json.load(f)
                logger.info(f"Loaded protocol catalog: {catalog_path}")
            
            # Load embedding models
            fast_model = os.getenv('EMBED_MODEL_FAST', self.config.get('embed_model_fast', 'sentence-transformers/all-MiniLM-L6-v2'))
            accurate_model = os.getenv('EMBED_MODEL_ACCURATE', self.config.get('embed_model_accurate', 'sentence-transformers/all-MiniLM-L6-v2'))
            cross_encoder_model = os.getenv('CROSS_ENCODER_MODEL', self.config.get('cross_encoder_model', ''))
            
            self.fast_embedder = get_embedder(fast_model)
            self.accurate_embedder = get_embedder(accurate_model)
            
            if cross_encoder_model:
                self.cross_encoder = get_cross_encoder(cross_encoder_model)
            
            logger.info("Hybrid retriever initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize hybrid retriever: {e}")
            raise
    
    def retrieve_fast(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """
        Fast lane retrieval using dense vectors and MMR finishing.
        
        Args:
            query: Query text
            top_k: Number of results to return (default: self.fast_return)
            
        Returns:
            List of retrieved documents
        """
        if top_k is None:
            top_k = self.fast_return
        
        if not self.fast_index or not self.fast_embedder:
            logger.error("Fast index or embedder not available")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.fast_embedder.model.encode([query])[0]
            
            # Search FAISS index
            scores, indices = self.fast_index.search(query_embedding, self.k_dense)
            
            # Get metadata for results
            metadata_list = self.fast_index.get_metadata_by_index(indices)
            
            # Create candidates
            candidates = []
            for i, (score, idx) in enumerate(zip(scores, indices)):
                if idx >= 0 and i < len(metadata_list):
                    candidate = {
                        'id': metadata_list[i].get('chunk_id', f'chunk_{idx}'),
                        'score': float(score),
                        'text': metadata_list[i].get('text', ''),
                        'metadata': metadata_list[i]
                    }
                    candidates.append(candidate)
            
            # Apply protocol boosting
            candidates = self._apply_protocol_boosting(candidates, query)
            
            # Apply fast finisher (MMR)
            candidate_embeddings = self._get_candidate_embeddings(candidates, self.fast_embedder.model)
            final_results = apply_fast_finisher(candidates, query_embedding, candidate_embeddings, top_k)
            
            logger.info(f"Fast retrieval returned {len(final_results)} results")
            return final_results
            
        except Exception as e:
            logger.error(f"Fast retrieval failed: {e}")
            return []
    
    def retrieve_accurate(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """
        Accurate lane retrieval using dense vectors, BM25, and cross-encoder finishing.
        
        Args:
            query: Query text
            top_k: Number of results to return (default: self.accurate_out)
            
        Returns:
            List of retrieved documents
        """
        if top_k is None:
            top_k = self.accurate_out
        
        if not self.accurate_index or not self.accurate_embedder:
            logger.error("Accurate index or embedder not available")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.accurate_embedder.model.encode([query])[0]
            
            # Dense retrieval
            scores, indices = self.accurate_index.search(query_embedding, self.k_dense)
            metadata_list = self.accurate_index.get_metadata_by_index(indices)
            
            dense_candidates = []
            for i, (score, idx) in enumerate(zip(scores, indices)):
                if idx >= 0 and i < len(metadata_list):
                    candidate = {
                        'id': metadata_list[i].get('chunk_id', f'chunk_{idx}'),
                        'score': float(score),
                        'text': metadata_list[i].get('text', ''),
                        'metadata': metadata_list[i]
                    }
                    dense_candidates.append(candidate)
            
            # BM25 retrieval (simplified - using text similarity)
            bm25_candidates = self._bm25_search(query, self.k_lex)
            
            # Combine with RRF
            combined_candidates = self._reciprocal_rank_fusion(dense_candidates, bm25_candidates)
            
            # Apply protocol boosting
            combined_candidates = self._apply_protocol_boosting(combined_candidates, query)
            
            # Apply accurate finisher (MMR + cross-encoder)
            candidate_embeddings = self._get_candidate_embeddings(combined_candidates, self.accurate_embedder.model)
            final_results = apply_accurate_finisher(
                combined_candidates, query, query_embedding, candidate_embeddings,
                self.cross_encoder.model if self.cross_encoder else None, top_k
            )
            
            logger.info(f"Accurate retrieval returned {len(final_results)} results")
            return final_results
            
        except Exception as e:
            logger.error(f"Accurate retrieval failed: {e}")
            return []
    
    def _bm25_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Simplified BM25 search using text similarity.
        
        Args:
            query: Query text
            top_k: Number of results to return
            
        Returns:
            List of BM25 candidates
        """
        # This is a simplified implementation
        # In production, you'd use a proper BM25 index like Elasticsearch or rank_bm25
        
        if not self.accurate_index:
            return []
        
        try:
            # Get all metadata for BM25 scoring
            all_metadata = self.accurate_index.load_metadata()
            if not all_metadata:
                return []
            
            # Simple TF-based scoring
            query_terms = query.lower().split()
            scored_candidates = []
            
            for i, metadata in enumerate(all_metadata):
                text = metadata.get('text', '').lower()
                score = 0.0
                
                for term in query_terms:
                    # Simple term frequency scoring
                    tf = text.count(term)
                    if tf > 0:
                        score += tf / len(text.split())  # Normalized TF
                
                if score > 0:
                    candidate = {
                        'id': metadata.get('chunk_id', f'chunk_{i}'),
                        'score': score,
                        'text': metadata.get('text', ''),
                        'metadata': metadata
                    }
                    scored_candidates.append(candidate)
            
            # Sort by score and return top_k
            scored_candidates.sort(key=lambda x: x['score'], reverse=True)
            return scored_candidates[:top_k]
            
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []
    
    def _reciprocal_rank_fusion(self, dense_candidates: List[Dict[str, Any]], 
                               bm25_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Combine dense and BM25 results using Reciprocal Rank Fusion.
        
        Args:
            dense_candidates: Dense retrieval results
            bm25_candidates: BM25 retrieval results
            
        Returns:
            Combined and reranked candidates
        """
        candidate_scores = {}
        
        # Add dense candidates
        for rank, candidate in enumerate(dense_candidates):
            candidate_id = candidate['id']
            rrf_score = 1.0 / (self.rrf_c + rank + 1)
            candidate_scores[candidate_id] = candidate_scores.get(candidate_id, 0.0) + rrf_score
        
        # Add BM25 candidates
        for rank, candidate in enumerate(bm25_candidates):
            candidate_id = candidate['id']
            rrf_score = 1.0 / (self.rrf_c + rank + 1)
            candidate_scores[candidate_id] = candidate_scores.get(candidate_id, 0.0) + rrf_score
        
        # Create combined candidates
        all_candidates = {c['id']: c for c in dense_candidates + bm25_candidates}
        combined_candidates = []
        
        for candidate_id, rrf_score in candidate_scores.items():
            if candidate_id in all_candidates:
                candidate = all_candidates[candidate_id].copy()
                candidate['score'] = rrf_score
                combined_candidates.append(candidate)
        
        # Sort by combined score
        combined_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        return combined_candidates
    
    def _apply_protocol_boosting(self, candidates: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Apply protocol catalog boosting to candidates.
        
        Args:
            candidates: List of candidates
            query: Query text
            
        Returns:
            Boosted candidates
        """
        if not self.protocol_catalog or not self.protocol_catalog.get('catalog'):
            return candidates
        
        try:
            # Get top protocol matches from catalog
            protocol_matches = self._get_protocol_matches(query)
            
            # Boost candidates from matching protocols
            boosted_candidates = []
            for candidate in candidates:
                boosted_candidate = candidate.copy()
                
                # Check if candidate belongs to a matching protocol
                protocol_id = candidate.get('metadata', {}).get('protocol_id', '')
                if protocol_id in protocol_matches:
                    boost = protocol_matches[protocol_id]
                    boosted_candidate['score'] += boost
                
                # Check for stone matches
                stones = candidate.get('metadata', {}).get('stones', [])
                stone_boost = 0.0
                for stone in stones[:3]:  # Max 3 stone boosts
                    if stone in self._extract_query_stones(query):
                        stone_boost += self.stone_boost
                
                boosted_candidate['score'] += min(stone_boost, self.stone_boost * 3)  # Cap at 3 boosts
                boosted_candidates.append(boosted_candidate)
            
            # Sort by boosted scores
            boosted_candidates.sort(key=lambda x: x['score'], reverse=True)
            return boosted_candidates
            
        except Exception as e:
            logger.error(f"Protocol boosting failed: {e}")
            return candidates
    
    def _get_protocol_matches(self, query: str) -> Dict[str, float]:
        """
        Get protocol matches from catalog for boosting.
        
        Args:
            query: Query text
            
        Returns:
            Dictionary of protocol_id -> boost_score
        """
        if not self.protocol_catalog:
            return {}
        
        try:
            catalog = self.protocol_catalog.get('catalog', {})
            protocol_matches = {}
            
            # Simple text matching for protocol boosting
            query_lower = query.lower()
            query_terms = set(query_lower.split())
            
            for protocol_id, protocol_data in catalog.items():
                # Check title and key phrases
                title = protocol_data.get('title', '').lower()
                key_phrases = protocol_data.get('key_phrases', [])
                
                match_score = 0.0
                
                # Title matching
                for term in query_terms:
                    if term in title:
                        match_score += 0.1
                
                # Key phrase matching
                for phrase in key_phrases:
                    if isinstance(phrase, str):
                        phrase_lower = phrase.lower()
                        for term in query_terms:
                            if term in phrase_lower:
                                match_score += 0.05
                
                if match_score > 0:
                    protocol_matches[protocol_id] = min(match_score * self.protocol_boost, self.protocol_boost)
            
            # Return top matches
            sorted_matches = sorted(protocol_matches.items(), key=lambda x: x[1], reverse=True)
            return dict(sorted_matches[:self.protocol_topn])
            
        except Exception as e:
            logger.error(f"Protocol matching failed: {e}")
            return {}
    
    def _extract_query_stones(self, query: str) -> List[str]:
        """Extract stone-related terms from query."""
        # Simple stone extraction - in production, you'd use more sophisticated NLP
        stone_indicators = ['light', 'form', 'flow', 'stone', 'foundation']
        query_lower = query.lower()
        
        found_stones = []
        for indicator in stone_indicators:
            if indicator in query_lower:
                found_stones.append(indicator)
        
        return found_stones
    
    def _get_candidate_embeddings(self, candidates: List[Dict[str, Any]], 
                                 embedder_model) -> np.ndarray:
        """
        Get embeddings for candidates.
        
        Args:
            candidates: List of candidates
            embedder_model: Embedding model
            
        Returns:
            Array of candidate embeddings
        """
        try:
            texts = [candidate.get('text', '') for candidate in candidates]
            embeddings = embedder_model.encode(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to get candidate embeddings: {e}")
            # Return zero embeddings as fallback
            if candidates:
                dimension = embedder_model.get_sentence_embedding_dimension()
                return np.zeros((len(candidates), dimension), dtype=np.float32)
            return np.array([])
    
    def get_info(self) -> Dict[str, Any]:
        """Get information about the retriever configuration."""
        return {
            "fast_index_loaded": self.fast_index is not None,
            "accurate_index_loaded": self.accurate_index is not None,
            "protocol_catalog_loaded": self.protocol_catalog is not None,
            "fast_embedder_model": self.fast_embedder.model_name if self.fast_embedder else None,
            "accurate_embedder_model": self.accurate_embedder.model_name if self.accurate_embedder else None,
            "cross_encoder_loaded": self.cross_encoder is not None,
            "k_dense": self.k_dense,
            "k_lex": self.k_lex,
            "rrf_c": self.rrf_c,
            "protocol_boost": self.protocol_boost,
            "stone_boost": self.stone_boost,
            "fast_return": self.fast_return,
            "accurate_out": self.accurate_out
        }


# -----------------------
# Convenience construction & shim API
# -----------------------
from typing import Optional, Dict, Any, List

def _infer_stats_path(index_path: Optional[str]) -> Optional[str]:
    if not index_path:
        return None
    p = str(index_path)
    if p.endswith(".faiss"):
        return p.replace(".faiss", ".stats.json")
    return p + ".stats.json"

def build_retriever(config: Optional[Dict[str, Any]] = None) -> "ProtocolFirstHybridRetriever":
    cfg = dict(config or {})

    fast_index_path = os.getenv("FAST_INDEX_PATH", cfg.get("fast_index_path"))
    fast_stats_path = os.getenv("FAST_STATS_PATH", cfg.get("fast_stats_path") or _infer_stats_path(fast_index_path))
    fast_meta_path  = os.getenv("FAST_META_PATH",  cfg.get("fast_meta_path"))

    accurate_index_path = os.getenv("ACCURATE_INDEX_PATH", cfg.get("accurate_index_path"))
    accurate_stats_path = os.getenv("ACCURATE_STATS_PATH", cfg.get("accurate_stats_path") or _infer_stats_path(accurate_index_path))
    accurate_meta_path  = os.getenv("ACCURATE_META_PATH",  cfg.get("accurate_meta_path"))

    protocol_catalog_path = os.getenv("PROTOCOL_CATALOG_PATH", cfg.get("protocol_catalog_path"))

    embed_model_fast     = os.getenv("EMBED_MODEL_FAST",     cfg.get("embed_model_fast", "sentence-transformers/all-MiniLM-L6-v2"))
    embed_model_accurate = os.getenv("EMBED_MODEL_ACCURATE", cfg.get("embed_model_accurate", "sentence-transformers/all-MiniLM-L6-v2"))
    cross_encoder_model  = os.getenv("CROSS_ENCODER_MODEL",  cfg.get("cross_encoder_model", ""))

    merged = {
        "fast_index_path": fast_index_path, "fast_stats_path": fast_stats_path, "fast_meta_path": fast_meta_path,
        "accurate_index_path": accurate_index_path, "accurate_stats_path": accurate_stats_path, "accurate_meta_path": accurate_meta_path,
        "protocol_catalog_path": protocol_catalog_path,
        "embed_model_fast": embed_model_fast, "embed_model_accurate": embed_model_accurate,
        "cross_encoder_model": cross_encoder_model,
    }
    return ProtocolFirstHybridRetriever(merged)

def retrieve(query_text: str, top_k: int = 8, lane: str = "fast"):
    r = build_retriever()
    lane = (lane or "fast").lower()
    if lane.startswith("acc"):
        return r.retrieve_accurate(query_text, top_k=top_k)
    return r.retrieve_fast(query_text, top_k=top_k)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", choices=["fast","accurate"], default="fast")
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("query", nargs="*", help="Query text")
    args = ap.parse_args()
    q = " ".join(args.query) or "how do I realign our sales stages to field reality?"
    res = retrieve(q, top_k=args.top_k, lane=args.lane)
    print(f"{len(res)} results ({args.lane})")
    for r in res[:args.top_k]:
        mid = (r.get("metadata") or {}).get("protocol_id", "?")
        print("-", mid, "→", (r.get("text","")[:80] + "..."))
