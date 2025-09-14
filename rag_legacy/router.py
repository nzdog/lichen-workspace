"""
Protocol Router for RAG system.

Maps queries to top 1-3 protocols using semantic similarity, stones alignment,
and keyword matching. Provides protocol filtering for scoped retrieval.
"""

import os
import json
import time
import pickle
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

# Optional imports with graceful degradation
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    HAS_EMBEDDING_DEPS = True
except ImportError:
    HAS_EMBEDDING_DEPS = False
    np = None
    SentenceTransformer = None

# Simple TF-IDF based router as fallback
from collections import Counter
import math

logger = logging.getLogger(__name__)


@dataclass
class ParsedQuery:
    """Parsed query with extracted signals."""
    normalized_text: str
    stones_signals: List[str]
    keywords: List[str]
    intents: List[str]


@dataclass
class RouteDecision:
    """Router decision with protocol candidates and confidence."""
    candidates: List[Dict[str, Any]]  # [{protocol_id, title, score}]
    confidence: float
    route: str  # "single", "double", "triple", or "all"


@dataclass
class ProtocolEntry:
    """Protocol catalog entry."""
    protocol_id: str
    title: str
    short_title: str
    stones: List[str]
    tags: List[str]
    fields: List[str]
    bridges: List[str]
    key_phrases: List[str]
    centroid_embedding: Optional[np.ndarray] = None


class ProtocolRouter:
    """Protocol router that maps queries to relevant protocols."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize router with configuration."""
        self.config = config
        self.router_config = config.get("router", {})
        self.catalog: Dict[str, ProtocolEntry] = {}
        self.embedding_model = None
        self.stones_synonyms = self._build_stones_synonyms()
        
        # Router configuration with defaults
        self.k = self.router_config.get("k", 3)
        self.min_conf_single = self.router_config.get("min_conf_single", 0.45)
        self.min_conf_double = self.router_config.get("min_conf_double", 0.30)
        self.min_conf_triple = self.router_config.get("min_conf_triple", 0.22)
        self.weights = self.router_config.get("weights", {
            "embed": 0.6,
            "stones": 0.2,
            "keywords": 0.2
        })
        self.cache_path = self.router_config.get("cache_path", ".vector/catalog_{model}.pkl")
        
        # Logging setup
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
    
    def _build_stones_synonyms(self) -> Dict[str, List[str]]:
        """Build mapping from synonyms to stones."""
        return {
            "stewardship": ["burnout", "burden", "weight", "heavy", "carrying", "load"],
            "wholeness": ["integrity", "whole", "complete", "aligned"],
            "speed": ["rushing", "haste", "urgency", "pace", "rhythm", "fast"],
            "trust": ["trust", "confidence", "reliability", "dependable"],
            "presence": ["present", "mindful", "aware", "conscious", "grounded"],
            "clarity": ["clarity", "clear", "clearly", "illuminate", "bright", "vision"],
            "light": ["light", "brightness", "illumination"],
            "form": ["structure", "framework", "system", "process", "method"]
        }
    
    def build_protocol_catalog(self, model_name: str = "all-MiniLM-L6-v2") -> Dict[str, ProtocolEntry]:
        """
        Build protocol catalog with embeddings.
        
        Args:
            model_name: Embedding model to use
            
        Returns:
            Dictionary mapping protocol_id to ProtocolEntry
        """
        if not HAS_EMBEDDING_DEPS:
            raise ImportError("Embedding dependencies not available. Install sentence-transformers, numpy")
        
        # Check cache first
        model_safe = model_name.replace("/", "_").replace("-", "_")
        cache_file = self.cache_path.replace("{model}", model_safe)
        if Path(cache_file).exists():
            logger.info(f"Loading protocol catalog from cache: {cache_file}")
            with open(cache_file, 'rb') as f:
                cached_data = pickle.load(f)
                if cached_data.get("model_name") == model_name:
                    self.catalog = cached_data["catalog"]
                    # Initialize embedding model even when loading from cache
                    self.embedding_model = SentenceTransformer(model_name)
                    return self.catalog
        
        logger.info(f"Building protocol catalog with model: {model_name}")
        
        # Load embedding model
        self.embedding_model = SentenceTransformer(model_name)
        
        # Load protocols
        protocols_dir = Path("protocols")
        if not protocols_dir.exists():
            # Try alternative paths
            alt_paths = [
                Path("../protocols"),
                Path("../../protocols"),
                Path("lichen-protocol-mvp/protocols")
            ]
            for alt_path in alt_paths:
                if alt_path.exists():
                    protocols_dir = alt_path
                    break
            else:
                raise FileNotFoundError("Protocols directory not found")
        
        catalog = {}
        protocol_files = list(protocols_dir.glob("*.json"))
        
        for protocol_file in protocol_files:
            try:
                with open(protocol_file, 'r') as f:
                    protocol_data = json.load(f)
                
                protocol_id = protocol_data.get("Protocol ID", protocol_file.stem)
                title = protocol_data.get("Title", "")
                short_title = protocol_data.get("Short Title", title)
                
                # Extract stones
                stones = protocol_data.get("Metadata", {}).get("Stones", [])
                if not isinstance(stones, list):
                    logger.warning(f"Stones is not a list in {protocol_file}: {type(stones)} - {stones}")
                    stones = []
                
                # Extract tags
                tags = protocol_data.get("Metadata", {}).get("Tags", [])
                if not isinstance(tags, list):
                    tags = []
                
                # Extract fields
                fields = protocol_data.get("Metadata", {}).get("Fields", [])
                if not isinstance(fields, list):
                    fields = []
                
                # Extract bridges
                bridges = protocol_data.get("Metadata", {}).get("Bridges", [])
                if not isinstance(bridges, list):
                    bridges = []
                
                # Extract key phrases from themes and outcomes
                key_phrases = self._extract_key_phrases(protocol_data)
                
                # Create protocol entry
                entry = ProtocolEntry(
                    protocol_id=protocol_id,
                    title=title,
                    short_title=short_title,
                    stones=stones,
                    tags=tags,
                    fields=fields,
                    bridges=bridges,
                    key_phrases=key_phrases
                )
                
                catalog[protocol_id] = entry
                
            except Exception as e:
                logger.warning(f"Failed to load protocol {protocol_file}: {e}")
                continue
        
        # Generate centroid embeddings
        logger.info(f"Generating centroid embeddings for {len(catalog)} protocols")
        for protocol_id, entry in catalog.items():
            entry.centroid_embedding = self._generate_centroid_embedding(entry)
        
        self.catalog = catalog
        
        # Cache the catalog
        cache_dir = Path(cache_file).parent
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        cache_data = {
            "model_name": model_name,
            "catalog": catalog,
            "created_at": time.time()
        }
        
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)
        
        logger.info(f"Cached protocol catalog to {cache_file}")
        return catalog
    
    def _extract_key_phrases(self, protocol_data: Dict[str, Any]) -> List[str]:
        """Extract key phrases from protocol data."""
        phrases = []
        
        # Add theme names
        themes = protocol_data.get("Themes", [])
        for theme in themes:
            theme_name = theme.get("Name", "")
            if theme_name:
                phrases.append(theme_name)
        
        # Add guiding questions (first few words)
        for theme in themes:
            questions = theme.get("Guiding Questions", [])
            for question in questions:
                # Extract first 3-5 words as key phrase
                words = question.split()[:5]
                if len(words) >= 3:
                    phrases.append(" ".join(words))
        
        # Add outcomes (short phrases from expected/excellent)
        for theme in themes:
            outcomes = theme.get("Outcomes", {})
            for outcome_type in ["Expected", "Excellent"]:
                outcome = outcomes.get(outcome_type, {})
                if isinstance(outcome, dict):
                    present_pattern = outcome.get("Present pattern", "")
                    if present_pattern:
                        # Extract short phrases (up to 6 words)
                        words = present_pattern.split()[:6]
                        if len(words) >= 3:
                            phrases.append(" ".join(words))
        
        # Add completion prompts (first few words)
        completion_prompts = protocol_data.get("Completion Prompts", [])
        for prompt in completion_prompts:
            words = prompt.split()[:4]
            if len(words) >= 2:
                phrases.append(" ".join(words))
        
        # Deduplicate and limit
        unique_phrases = list(set(phrases))
        return unique_phrases[:20]  # Limit to 20 key phrases
    
    def _generate_centroid_embedding(self, entry: ProtocolEntry) -> np.ndarray:
        """Generate centroid embedding for a protocol entry."""
        texts_to_embed = []
        
        # Add title
        if entry.title:
            texts_to_embed.append(entry.title)
        
        # Add theme names (from stones)
        for stone in entry.stones:
            if isinstance(stone, str):
                texts_to_embed.append(stone.replace("-", " "))
            elif isinstance(stone, dict):
                # Handle case where stone is a dict with 'slug' or 'name' field
                stone_text = stone.get('slug', stone.get('name', str(stone)))
                texts_to_embed.append(stone_text.replace("-", " "))
        
        # Add key phrases
        texts_to_embed.extend(entry.key_phrases)
        
        # Add tags and fields
        texts_to_embed.extend(entry.tags)
        texts_to_embed.extend(entry.fields)
        
        if not texts_to_embed:
            # Fallback to protocol_id
            texts_to_embed = [entry.protocol_id]
        
        # Generate embeddings and average
        embeddings = self.embedding_model.encode(texts_to_embed)
        centroid = np.mean(embeddings, axis=0)
        
        # Normalize
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm
        
        return centroid
    
    def parse_query(self, query: str) -> ParsedQuery:
        """
        Parse query to extract signals.
        
        Args:
            query: Input query string
            
        Returns:
            ParsedQuery with extracted signals
        """
        # Normalize text
        normalized_text = re.sub(r'[^\w\s]', ' ', query.lower()).strip()
        
        # Extract stones signals
        stones_signals = []
        for stone, synonyms in self.stones_synonyms.items():
            for synonym in synonyms:
                if synonym in normalized_text:
                    stones_signals.append(stone)
                    break
        
        # Extract keywords (simple approach - could be enhanced with NLP)
        words = normalized_text.split()
        keywords = [word for word in words if len(word) > 3 and word not in 
                   ["what", "when", "where", "why", "how", "this", "that", "with", "from", "they", "have", "been", "were"]]
        
        # Extract intents (simple keyword-based)
        intents = []
        if any(word in normalized_text for word in ["help", "support", "guidance", "advice"]):
            intents.append("support")
        if any(word in normalized_text for word in ["how", "what", "when", "where"]):
            intents.append("information")
        if any(word in normalized_text for word in ["problem", "issue", "struggle", "difficult"]):
            intents.append("problem_solving")
        if any(word in normalized_text for word in ["protocol", "process", "method", "approach"]):
            intents.append("protocol_selection")
        
        return ParsedQuery(
            normalized_text=normalized_text,
            stones_signals=stones_signals,
            keywords=keywords,
            intents=intents
        )
    
    def route_query(self, parsed: ParsedQuery, k: int = None) -> RouteDecision:
        """
        Route query to top protocol candidates.
        
        Args:
            parsed: Parsed query
            k: Number of candidates to consider (defaults to config)
            
        Returns:
            RouteDecision with candidates and confidence
        """
        if k is None:
            k = self.k
        
        if not self.catalog:
            logger.warning("Protocol catalog not loaded, returning empty decision")
            return RouteDecision(candidates=[], confidence=0.0, route="all")
        
        # Always use enhanced keyword-only routing (TF-IDF based)
        logger.info("Using enhanced TF-IDF based routing")
        return self._route_keywords_only(parsed, k)
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([parsed.normalized_text])[0]
        
        # Score all protocols
        scores = []
        for protocol_id, entry in self.catalog.items():
            score = self._score_protocol(parsed, query_embedding, entry)
            scores.append({
                "protocol_id": protocol_id,
                "title": entry.title,
                "score": score
            })
        
        # Sort by score
        scores.sort(key=lambda x: x["score"], reverse=True)
        
        # Get top candidates
        candidates = scores[:k]
        
        # Determine confidence and route
        confidence = candidates[0]["score"] if candidates else 0.0
        
        if confidence >= self.min_conf_single:
            route = "single"
            final_candidates = candidates[:1]
        elif confidence >= self.min_conf_double:
            route = "double"
            final_candidates = candidates[:2]
        elif confidence >= self.min_conf_triple:
            route = "triple"
            final_candidates = candidates[:3]
        else:
            route = "all"
            final_candidates = []
        
        # Log decision
        self._log_decision(parsed, candidates, confidence, route)
        
        return RouteDecision(
            candidates=final_candidates,
            confidence=confidence,
            route=route
        )
    
    def _score_protocol(self, parsed: ParsedQuery, query_embedding: np.ndarray, entry: ProtocolEntry) -> float:
        """Score a protocol against parsed query."""
        scores = []
        
        # Embedding similarity (0.6 weight)
        if entry.centroid_embedding is not None:
            embed_sim = float(np.dot(query_embedding, entry.centroid_embedding))
            scores.append(("embed", embed_sim, self.weights["embed"]))
        
        # Stones overlap (0.2 weight)
        stones_overlap = self._jaccard_overlap(parsed.stones_signals, entry.stones)
        scores.append(("stones", stones_overlap, self.weights["stones"]))
        
        # Keyword match (0.2 weight)
        keyword_score = self._keyword_match(parsed.keywords, entry.tags + entry.key_phrases + entry.fields)
        scores.append(("keywords", keyword_score, self.weights["keywords"]))
        
        # Weighted average
        total_score = sum(score * weight for _, score, weight in scores)
        total_weight = sum(weight for _, _, weight in scores)
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _jaccard_overlap(self, list1: List[str], list2: List[str]) -> float:
        """Calculate Jaccard overlap between two lists."""
        if not list1 or not list2:
            return 0.0
        
        # Convert to strings to handle dict objects
        set1 = set(str(item) for item in list1)
        set2 = set(str(item) for item in list2)
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _keyword_match(self, keywords: List[str], target_terms: List[str]) -> float:
        """Calculate keyword match score."""
        if not keywords or not target_terms:
            return 0.0
        
        matches = 0
        for keyword in keywords:
            for term in target_terms:
                # Handle case where term might be a dict
                if isinstance(term, str):
                    term_text = term.lower()
                elif isinstance(term, dict):
                    term_text = str(term).lower()
                else:
                    term_text = str(term).lower()
                
                if keyword in term_text or term_text in keyword:
                    matches += 1
                    break
        
        return matches / len(keywords)
    
    def _compute_tfidf(self, text: str) -> Dict[str, float]:
        """Compute TF-IDF scores for text."""
        # Simple tokenization
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
        words = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Compute term frequencies
        tf = Counter(words)
        total_words = len(words)
        
        # Normalize TF
        tf_normalized = {word: count / total_words for word, count in tf.items()}
        
        return tf_normalized
    
    def _cosine_similarity(self, tfidf1: Dict[str, float], tfidf2: Dict[str, float]) -> float:
        """Compute cosine similarity between two TF-IDF vectors."""
        # Get all unique words
        all_words = set(tfidf1.keys()) | set(tfidf2.keys())
        
        if not all_words:
            return 0.0
        
        # Compute dot product and magnitudes
        dot_product = sum(tfidf1.get(word, 0) * tfidf2.get(word, 0) for word in all_words)
        magnitude1 = math.sqrt(sum(tfidf1.get(word, 0) ** 2 for word in all_words))
        magnitude2 = math.sqrt(sum(tfidf2.get(word, 0) ** 2 for word in all_words))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _route_keywords_only(self, parsed: ParsedQuery, k: int) -> RouteDecision:
        """Fallback routing using TF-IDF and keyword matching."""
        scores = []
        
        # Build TF-IDF scores for better semantic matching
        query_tfidf = self._compute_tfidf(parsed.normalized_text)
        
        for protocol_id, entry in self.catalog.items():
            # Combine multiple scoring methods
            score = 0.0
            
            # 1. TF-IDF similarity (0.4 weight)
            protocol_text = f"{entry.title} {' '.join(entry.key_phrases)} {' '.join(entry.tags)}"
            protocol_tfidf = self._compute_tfidf(protocol_text)
            tfidf_sim = self._cosine_similarity(query_tfidf, protocol_tfidf)
            score += tfidf_sim * 0.4
            
            # 2. Title keyword match (0.3 weight)
            title_score = self._keyword_match(parsed.keywords, [entry.title])
            score += title_score * 0.3
            
            # 3. Stones alignment (0.2 weight)
            stones_overlap = self._jaccard_overlap(parsed.stones_signals, entry.stones)
            score += stones_overlap * 0.2
            
            # 4. Tags/key phrases match (0.1 weight)
            keyword_score = self._keyword_match(parsed.keywords, entry.tags + entry.key_phrases)
            score += keyword_score * 0.1
            
            scores.append({
                "protocol_id": protocol_id,
                "title": entry.title,
                "score": score
            })
        
        scores.sort(key=lambda x: x["score"], reverse=True)
        candidates = scores[:k]
        confidence = candidates[0]["score"] if candidates else 0.0
        
        # Use adjusted confidence thresholds for TF-IDF
        if confidence >= 0.25:  # Lower threshold for single
            route = "single"
            final_candidates = candidates[:1]
        elif confidence >= 0.20:  # Lower threshold for double
            route = "double"
            final_candidates = candidates[:2]
        elif confidence >= 0.15:  # Lower threshold for triple
            route = "triple"
            final_candidates = candidates[:3]
        else:
            route = "all"
            final_candidates = []
        
        return RouteDecision(
            candidates=final_candidates,
            confidence=confidence,
            route=route
        )
    
    def _log_decision(self, parsed: ParsedQuery, candidates: List[Dict[str, Any]], 
                     confidence: float, route: str):
        """Log router decision for debugging and evaluation."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"router_{timestamp}.log"
        
        log_entry = {
            "timestamp": time.time(),
            "query": parsed.normalized_text,
            "stones_signals": parsed.stones_signals,
            "keywords": parsed.keywords,
            "intents": parsed.intents,
            "candidates": candidates,
            "confidence": confidence,
            "route": route
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_entry, f, indent=2)
        
        logger.info(f"Router decision logged to {log_file}")


def build_protocol_catalog(model_name: str = "all-MiniLM-L6-v2") -> Dict[str, ProtocolEntry]:
    """Build protocol catalog with embeddings."""
    # Load config with robust path resolution
    config = {"router": {}}  # Default config
    
    # Try multiple possible config locations
    possible_paths = [
        Path("config/rag.yaml"),  # Current directory
        Path("../config/rag.yaml"),  # Parent directory (for eval/ context)
        Path("../../config/rag.yaml"),  # Grandparent directory
        Path("lichen-protocol-mvp/config/rag.yaml"),  # From lichen-protocol-mvp
        Path("../lichen-protocol-mvp/config/rag.yaml"),  # From eval/ context
    ]
    
    config_path = None
    for path in possible_paths:
        if path.exists():
            config_path = path
            break
    
    if config_path:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    
    # Ensure config has router section
    if "router" not in config:
        config["router"] = {}
    
    router = ProtocolRouter(config)
    return router.build_protocol_catalog(model_name)


def parse_query(query: str) -> ParsedQuery:
    """Parse query to extract signals."""
    config = {"router": {}}
    router = ProtocolRouter(config)
    return router.parse_query(query)


def route_query(parsed: ParsedQuery, k: int = 3) -> RouteDecision:
    """Route parsed query to protocol candidates."""
    try:
        # Load config with robust path resolution
        config = {"router": {}}  # Default config
        
        # Try multiple possible config locations
        possible_paths = [
            Path("config/rag.yaml"),  # Current directory
            Path("../config/rag.yaml"),  # Parent directory (for eval/ context)
            Path("../../config/rag.yaml"),  # Grandparent directory
            Path("lichen-protocol-mvp/config/rag.yaml"),  # From lichen-protocol-mvp
            Path("../lichen-protocol-mvp/config/rag.yaml"),  # From eval/ context
        ]
        
        config_path = None
        for path in possible_paths:
            if path.exists():
                config_path = path
                break
        
        if config_path:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
    
        # Ensure config has router section
        if "router" not in config:
            config["router"] = {}
        
        router = ProtocolRouter(config)
        
        # Load catalog if not already loaded
        if not router.catalog:
            model_name = "all-MiniLM-L6-v2"
            router.build_protocol_catalog(model_name)
        
        return router.route_query(parsed, k)
    except Exception as e:
        print(f"Router error in route_query: {e}")
        import traceback
        traceback.print_exc()
        # Return empty decision on error
        return RouteDecision(candidates=[], confidence=0.0, route="all")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Protocol Router CLI")
    parser.add_argument("command", choices=["build-catalog", "test-route"], help="Command to run")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2", help="Embedding model")
    parser.add_argument("--query", help="Query to test routing")
    
    args = parser.parse_args()
    
    if args.command == "build-catalog":
        print(f"Building protocol catalog with model: {args.model}")
        catalog = build_protocol_catalog(args.model)
        print(f"Built catalog with {len(catalog)} protocols")
        
        # Print sample entries
        for i, (protocol_id, entry) in enumerate(list(catalog.items())[:3]):
            print(f"\n{i+1}. {protocol_id}")
            print(f"   Title: {entry.title}")
            print(f"   Stones: {entry.stones}")
            print(f"   Key phrases: {entry.key_phrases[:3]}...")
    
    elif args.command == "test-route":
        if not args.query:
            print("Error: --query required for test-route")
            exit(1)
        
        print(f"Testing routing for query: {args.query}")
        parsed = parse_query(args.query)
        print(f"Parsed: {parsed}")
        
        decision = route_query(parsed)
        print(f"Route decision: {decision}")
