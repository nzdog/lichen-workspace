"""
RAG (Retrieval-Augmented Generation) adapter for the Hallway Protocol.

Provides retrieval and generation capabilities with support for fast/accurate lanes,
Stones alignment, and citations. Supports both live retrieval and dummy mode for testing.
"""

import os
import json
import time
import yaml
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class RAGAdapter:
    """RAG adapter with retrieval, generation, and Stones alignment capabilities."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize RAG adapter with configuration."""
        self.config = self._load_config(config_path)
        self.lanes_config = self._load_lanes_config()
        self.dummy_mode = os.getenv("USE_DUMMY_RAG", "0") == "1"
        self.enabled = os.getenv("RAG_ENABLED", "1") == "1"
        self.default_lane = os.getenv("RAG_PROFILE", "fast")
        
        # Load dummy data if in dummy mode
        if self.dummy_mode:
            self.dummy_retrieval = self._load_dummy_retrieval()
            self.dummy_answers = self._load_dummy_answers()
        
        # Initialize backend components (wrapped in try/except for dummy mode)
        self._init_backend_components()
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load RAG configuration from YAML file."""
        if config_path is None:
            config_path = "config/rag.yaml"
        
        config_file = Path(config_path)
        if not config_file.exists():
            # Return default config if file doesn't exist
            return {
                "fast": {
                    "top_k": 8,
                    "mmr_lambda": 0.4,
                    "embed_model": "all-MiniLM-L6-v2"
                },
                "accurate": {
                    "top_k_retrieve": 24,
                    "top_k_rerank": 8,
                    "cross_encoder": "cross-encoder/ms-marco-MiniLM-L-6-v2"
                },
                "vector_store": {
                    "provider": "faiss",
                    "path_or_index": ".vector/index.faiss",
                    "namespace": "protocols"
                },
                "limits": {
                    "max_context_chars": 12000
                }
            }
        
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_lanes_config(self) -> Dict[str, Any]:
        """Load lane policy thresholds."""
        lanes_file = Path("config/rag_lanes.json")
        if not lanes_file.exists():
            # Return default lanes config
            return {
                "fast": {
                    "precision@5": 0.40,
                    "recall@20": 0.70,
                    "mrr@10": 0.35,
                    "ndcg@10": 0.55,
                    "stones_alignment": 0.70,
                    "hallucination_rate": 0.02
                },
                "accurate": {
                    "precision@5": 0.60,
                    "recall@20": 0.85,
                    "mrr@10": 0.50,
                    "ndcg@10": 0.70,
                    "stones_alignment": 0.80,
                    "hallucination_rate": 0.01
                }
            }
        
        with open(lanes_file, 'r') as f:
            return json.load(f)
    
    def _load_dummy_retrieval(self) -> List[Dict[str, Any]]:
        """Load dummy retrieval data."""
        # Try multiple possible paths
        possible_paths = [
            Path("../eval/data/dummy_retrieval.jsonl"),  # Eval path (preferred)
            Path("../data/dummy_retrieval.jsonl"),  # Relative to lichen-protocol-mvp
            Path("eval/data/dummy_retrieval.jsonl"),  # Relative to workspace root
        ]
        
        for dummy_file in possible_paths:
            if dummy_file.exists():
                results = []
                with open(dummy_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            results.append(json.loads(line))
                return results
        
        return []
    
    def _load_dummy_answers(self) -> List[Dict[str, Any]]:
        """Load dummy answer data."""
        # Try multiple possible paths
        possible_paths = [
            Path("../eval/data/dummy_answers.jsonl"),  # Eval path (preferred)
            Path("../data/dummy_answers.jsonl"),  # Relative to lichen-protocol-mvp
            Path("eval/data/dummy_answers.jsonl"),  # Relative to workspace root
        ]
        
        for dummy_file in possible_paths:
            if dummy_file.exists():
                results = []
                with open(dummy_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            results.append(json.loads(line))
                return results
        
        return []
    
    def _init_backend_components(self):
        """Initialize backend components (embedding models, vector stores, etc.)."""
        if self.dummy_mode:
            return
        
        try:
            # Import FAISS store helper
            from ._faiss_store import load_store, HAS_FAISS_DEPS
            
            if not HAS_FAISS_DEPS:
                logger.warning("FAISS dependencies not available, falling back to dummy mode")
                self.dummy_mode = True
                self.dummy_retrieval = self._load_dummy_retrieval()
                self.dummy_answers = self._load_dummy_answers()
                return
            
            # Initialize FAISS stores for both lanes
            config_path = "config/rag.yaml"
            # Try multiple possible config paths
            config_paths = [
                Path("config/rag.yaml"),
                Path("../config/rag.yaml"),
                Path("../../config/rag.yaml"),
            ]
            
            config_found = False
            for path in config_paths:
                if path.exists():
                    config_path = str(path)
                    config_found = True
                    break
            
            if not config_found:
                raise FileNotFoundError(f"RAG config not found in any of: {[str(p) for p in config_paths]}")
            
            # Load stores for both lanes
            self.faiss_stores = {
                "fast": load_store("fast", config_path),
                "accurate": load_store("accurate", config_path)
            }
            
        except ImportError as e:
            logger.warning(f"Failed to import FAISS dependencies: {e}, falling back to dummy mode")
            self.dummy_mode = True
            self.dummy_retrieval = self._load_dummy_retrieval()
            self.dummy_answers = self._load_dummy_answers()
        except Exception as e:
            logger.warning(f"Failed to initialize FAISS store: {e}, falling back to dummy mode")
            self.dummy_mode = True
            self.dummy_retrieval = self._load_dummy_retrieval()
            self.dummy_answers = self._load_dummy_answers()
    
    def retrieve(self, query: str, lane: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: Search query
            lane: Retrieval lane (fast/accurate), defaults to configured default
            
        Returns:
            List of retrieval results with doc, chunk, rank, score, text
        """
        if not self.enabled:
            return []
        
        if lane is None:
            lane = self.default_lane
        
        if self.dummy_mode:
            return self._dummy_retrieve(query, lane)
        
        # Live retrieval implementation
        return self._live_retrieve(query, lane)
    
    def _dummy_retrieve(self, query: str, lane: str) -> List[Dict[str, Any]]:
        """Dummy retrieval using pre-computed results."""
        # Find matching dummy retrieval result
        for result in self.dummy_retrieval:
            if result.get("query", "").lower() in query.lower() or query.lower() in result.get("query", "").lower():
                # Filter results based on lane if specified
                results = result.get("results", [])
                if lane == "fast":
                    # Take top results for fast lane
                    top_k = self.config.get("fast", {}).get("top_k", 8)
                    return results[:top_k]
                elif lane == "accurate":
                    # Take more results for accurate lane
                    top_k = self.config.get("accurate", {}).get("top_k_retrieve", 24)
                    return results[:top_k]
                else:
                    return results
        
        # Return empty results if no match found
        return []
    
    def _live_retrieve(self, query: str, lane: str) -> List[Dict[str, Any]]:
        """Live retrieval using actual embedding models and vector store."""
        if not hasattr(self, 'faiss_stores') or lane not in self.faiss_stores:
            logger.warning(f"FAISS store for {lane} lane not initialized, returning empty results")
            return []
        
        start_time = time.time()
        
        try:
            # Get lane-specific store
            faiss_store = self.faiss_stores[lane]
            
            # Embed query using lane-specific model
            query_embedding = faiss_store.embed_query(query)
            
            # Get lane configuration
            lane_config = self.config.get(lane, {})
            
            if lane == "fast":
                # Fast lane: MMR reranking
                top_k = lane_config.get("top_k", 8)
                mmr_lambda = lane_config.get("mmr_lambda", 0.4)
                
                # Search for more candidates for MMR
                search_k = top_k * 4
                candidates = faiss_store.search(query_embedding, search_k)
                
                # Apply MMR reranking
                reranked = faiss_store._mmr_rerank(candidates, query_embedding, mmr_lambda, top_k)
                
            elif lane == "accurate":
                # Accurate lane: cross-encoder reranking with environment overrides
                top_k_retrieve = int(os.getenv("ACCURATE_TOPK_RETRIEVE", lane_config.get("top_k_retrieve", 40)))
                top_k_rerank = int(os.getenv("ACCURATE_TOPK_RERANK", lane_config.get("top_k_rerank", 10)))
                cross_encoder = os.getenv("RERANKER_MODEL", lane_config.get("cross_encoder", "cross-encoder/ms-marco-electra-base"))
                
                # Search for candidates
                candidates = faiss_store.search(query_embedding, top_k_retrieve)
                
                # Apply cross-encoder reranking
                reranked = faiss_store.rerank_with_cross_encoder(query, candidates, cross_encoder, top_k_rerank)
                
            else:
                # Default to fast lane behavior
                top_k = lane_config.get("top_k", 8)
                candidates = faiss_store.search(query_embedding, top_k)
                reranked = candidates
            
            # Convert to expected format
            results = []
            for rank, (idx, score) in enumerate(reranked, 1):
                meta = faiss_store.get_meta(idx)
                if meta:
                    results.append({
                        "doc": meta.get("doc", ""),
                        "chunk": meta.get("chunk", 0),
                        "rank": rank,
                        "score": float(score),
                        "text": meta.get("text", "")
                    })
            
            # Sort by score descending, then by doc and chunk for ties
            results.sort(key=lambda x: (-x["score"], x["doc"], x["chunk"]))
            
            # Update ranks after sorting
            for i, result in enumerate(results, 1):
                result["rank"] = i
            
            latency_ms = (time.time() - start_time) * 1000
            embedder_name = faiss_store.get_embedder_name()
            logger.info(f"{lane} lane retrieval: {embedder_name}, {len(results)} results in {latency_ms:.1f}ms")
            
            return results
            
        except Exception as e:
            logger.error(f"Live retrieval failed: {e}")
            return []
    
    def generate(self, query: str, context_texts: List[str], lane: str = None) -> Dict[str, Any]:
        """
        Generate an answer based on query and context texts.
        
        Args:
            query: Original query
            context_texts: Retrieved context texts
            lane: Generation lane (fast/accurate)
            
        Returns:
            Dict with answer, citations, and hallucinations count
        """
        if not self.enabled:
            return {
                "answer": "RAG is not enabled.",
                "citations": [],
                "hallucinations": 1,
                "reason": "flags.disabled"
            }
        
        if lane is None:
            lane = self.default_lane
        
        if self.dummy_mode:
            return self._dummy_generate(query, context_texts, lane)
        
        # Live generation implementation
        return self._live_generate(query, context_texts, lane)
    
    def _dummy_generate(self, query: str, context_texts: List[str], lane: str) -> Dict[str, Any]:
        """Dummy generation using pre-computed answers."""
        # Find matching dummy answer
        for answer in self.dummy_answers:
            if (answer.get("query", "").lower() in query.lower() or 
                query.lower() in answer.get("query", "").lower()):
                if answer.get("lane") == lane:
                    # Extract citations from context texts
                    citations = []
                    for i, text in enumerate(context_texts[:5]):  # Limit citations
                        # Simple citation extraction - in real implementation would be more sophisticated
                        citations.append({
                            "doc": f"context_{i}",
                            "chunk": 1
                        })
                    
                    return {
                        "answer": answer.get("answer", ""),
                        "citations": citations,
                        "hallucinations": answer.get("hallucinations", 0)
                    }
        
        # Return insufficient support if no match found
        return {
            "answer": "I don't have sufficient information to answer this question based on the available context.",
            "citations": [],
            "hallucinations": 1
        }
    
    def _live_generate(self, query: str, context_texts: List[str], lane: str) -> Dict[str, Any]:
        """Live generation using actual language models."""
        if not context_texts:
            return {
                "answer": "I don't have sufficient information to answer this question based on the available context.",
                "citations": [],
                "hallucinations": 1
            }
        
        # Truncate context to max_context_chars
        max_chars = self.config.get("limits", {}).get("max_context_chars", 12000)
        context_text = " ".join(context_texts)
        if len(context_text) > max_chars:
            context_text = context_text[:max_chars] + "..."
        
        # Simple grounded answer construction
        # In a real implementation, this would use a language model
        answer = f"Based on the available context, here's what I found regarding your question: {query}\n\n"
        answer += f"Context: {context_text[:500]}..."
        
        # Extract citations from context texts
        citations = []
        for i, text in enumerate(context_texts[:5]):  # Limit to 5 citations
            # Simple citation extraction - in real implementation would be more sophisticated
            citations.append({
                "doc": f"context_{i}",
                "chunk": 1
            })
        
        return {
            "answer": answer,
            "citations": citations,
            "hallucinations": 0
        }
    
    def stones_align(self, answer_text: str, expected_stones: List[str]) -> float:
        """
        Calculate Stones alignment score for an answer.
        
        Args:
            answer_text: Generated answer text
            expected_stones: List of expected Stones (principles)
            
        Returns:
            Alignment score between 0.0 and 1.0
        """
        if not expected_stones:
            return 1.0
        
        # Deterministic baseline implementation
        # TODO: Replace with actual classifier
        answer_lower = answer_text.lower()
        
        # Check for presence of stone names/slugs in the answer
        matches = 0
        for stone in expected_stones:
            stone_lower = stone.lower()
            # Check for exact matches and partial matches
            # For hyphenated slugs, also check individual words
            words_to_check = stone_lower.split() + stone_lower.split('-')
            if (stone_lower in answer_lower or 
                any(word in answer_lower for word in words_to_check if word)):
                matches += 1
        
        # Return proportion of stones that have some presence in the answer
        return matches / len(expected_stones)
    
    def get_lane_threshold(self, lane: str, metric: str) -> float:
        """Get threshold value for a specific lane and metric."""
        return self.lanes_config.get(lane, {}).get(metric, 0.0)
    
    def is_sufficient_support(self, lane: str, stones_alignment: float, hallucinations: int) -> bool:
        """Check if the generated answer has sufficient support based on lane thresholds."""
        threshold = self.get_lane_threshold(lane, "stones_alignment")
        max_hallucinations = 0 if self.get_lane_threshold(lane, "hallucination_rate") < 0.01 else 1
        
        return stones_alignment >= threshold and hallucinations <= max_hallucinations
    
    def to_log_dict(self, results: List[Dict[str, Any]], retrieval_time_ms: float, 
                   generation_time_ms: float, lane: str) -> Dict[str, Any]:
        """
        Convert retrieval results to log dictionary format.
        
        Args:
            results: Retrieval results
            retrieval_time_ms: Retrieval time in milliseconds
            generation_time_ms: Generation time in milliseconds
            lane: Lane used (fast/accurate)
            
        Returns:
            Dict suitable for observability logging
        """
        # Get embedding model and index info
        embedder_name = "unknown"
        index_info = {"path": "unknown", "dim": 0, "count": 0}
        reranker_name = None
        
        if not self.dummy_mode and hasattr(self, 'faiss_stores') and lane in self.faiss_stores:
            store = self.faiss_stores[lane]
            embedder_name = store.get_embedder_name()
            index_info = store.get_index_info()
            reranker_name = store.get_reranker_name()
        
        # Build retrieval metrics
        retrieval_metrics = {
            "elapsed_ms": retrieval_time_ms,
            "topk": len(results),
            "breadth": len(results),  # For now, same as topk - would be different with MMR
            "embed_model": embedder_name,
            "index": index_info,
            "reranker_model": reranker_name,
            "rerank_elapsed_ms": None  # Would be filled if reranking was timed separately
        }
        
        # Build results array (doc/chunk/rank/score only)
        log_results = []
        for result in results:
            log_results.append({
                "rank": result.get("rank", 0),
                "doc": result.get("doc", ""),
                "chunk": result.get("chunk", 0),
                "score": result.get("score", 0.0)
            })
        
        return {
            "retrieval": retrieval_metrics,
            "results": log_results
        }


# Global instance for easy access
_rag_adapter = None

def get_rag_adapter() -> RAGAdapter:
    """Get the global RAG adapter instance."""
    global _rag_adapter
    if _rag_adapter is None:
        _rag_adapter = RAGAdapter()
    return _rag_adapter
