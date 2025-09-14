"""
Tests for Protocol Router and RAG integration.

Tests router functionality, retrieval integration, and end-to-end routing.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

# Import the modules we're testing
import sys
sys.path.append(str(Path(__file__).parent.parent))

from rag.router import ProtocolRouter, ParsedQuery, RouteDecision, ProtocolEntry
sys.path.append(str(Path(__file__).parent.parent / "lichen-protocol-mvp"))
from hallway.adapters.rag_adapter import RAGAdapter


class TestProtocolRouter:
    """Test Protocol Router functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_config = {
            "router": {
                "enabled": True,
                "k": 3,
                "min_conf_single": 0.45,
                "min_conf_double": 0.30,
                "min_conf_triple": 0.22,
                "weights": {
                    "embed": 0.6,
                    "stones": 0.2,
                    "keywords": 0.2
                },
                "cache_path": ".vector/catalog_{model}.pkl"
            }
        }
        
        # Create test protocol entries
        self.test_protocols = {
            "leadership_carrying": ProtocolEntry(
                protocol_id="leadership_carrying",
                title="The Leadership I'm Actually Carrying",
                short_title="Leadership Carrying",
                stones=["stewardship", "wholeness"],
                tags=["leadership", "burden", "weight"],
                fields=["leadership", "stewardship"],
                bridges=[],
                key_phrases=["hidden load", "leadership burden", "carrying weight", "stewardship responsibility"]
            ),
            "pace_gate": ProtocolEntry(
                protocol_id="pace_gate",
                title="Pace Gate",
                short_title="Pace Gate",
                stones=["speed", "trust"],
                tags=["pace", "rhythm", "speed"],
                fields=["pace", "rhythm"],
                bridges=[],
                key_phrases=["rushing", "pace adjustment", "rhythm", "speed control"]
            ),
            "mirror": ProtocolEntry(
                protocol_id="mirror",
                title="Mirror Protocol",
                short_title="Mirror",
                stones=["presence", "clarity"],
                tags=["reflection", "mirror", "clarity"],
                fields=["presence", "clarity"],
                bridges=[],
                key_phrases=["reflect back", "mirror words", "clear reflection", "presence"]
            )
        }
    
    def test_parse_query(self):
        """Test query parsing functionality."""
        router = ProtocolRouter(self.test_config)
        
        # Test leadership query
        query = "leadership feels heavy / hidden load"
        parsed = router.parse_query(query)
        
        assert parsed.normalized_text == "leadership feels heavy hidden load"
        assert "stewardship" in parsed.stones_signals  # "heavy" should map to stewardship
        assert "leadership" in parsed.keywords
        assert "hidden" in parsed.keywords
        assert "load" in parsed.keywords
        
        # Test pace query
        query = "I'm rushing and losing trust / pace off"
        parsed = router.parse_query(query)
        
        assert "speed" in parsed.stones_signals  # "rushing" should map to speed
        assert "trust" in parsed.stones_signals
        assert "rushing" in parsed.keywords
        assert "pace" in parsed.keywords
    
    def test_route_query_keywords_only(self):
        """Test routing using only keyword matching (fallback mode)."""
        router = ProtocolRouter(self.test_config)
        router.catalog = self.test_protocols
        
        # Test leadership query
        parsed = ParsedQuery(
            normalized_text="leadership feels heavy hidden load",
            stones_signals=["stewardship"],
            keywords=["leadership", "heavy", "hidden", "load"],
            intents=["support"]
        )
        
        decision = router._route_keywords_only(parsed, k=3)
        
        assert decision.route in ["single", "double", "triple", "all"]
        assert 0.0 <= decision.confidence <= 1.0
        assert len(decision.candidates) <= 3
        
        # Should route to leadership_carrying
        if decision.candidates:
            top_candidate = decision.candidates[0]
            assert top_candidate["protocol_id"] == "leadership_carrying"
    
    def test_route_query_pace(self):
        """Test routing for pace-related query."""
        router = ProtocolRouter(self.test_config)
        router.catalog = self.test_protocols
        
        parsed = ParsedQuery(
            normalized_text="rushing and losing trust pace off",
            stones_signals=["speed", "trust"],
            keywords=["rushing", "trust", "pace"],
            intents=["problem_solving"]
        )
        
        decision = router._route_keywords_only(parsed, k=3)
        
        # Should route to pace_gate
        if decision.candidates:
            top_candidate = decision.candidates[0]
            assert top_candidate["protocol_id"] == "pace_gate"
    
    def test_route_query_mirror(self):
        """Test routing for mirror-related query."""
        router = ProtocolRouter(self.test_config)
        router.catalog = self.test_protocols
        
        parsed = ParsedQuery(
            normalized_text="reflect back my words clearly",
            stones_signals=["presence", "clarity"],
            keywords=["reflect", "words", "clearly"],
            intents=["information"]
        )
        
        decision = router._route_keywords_only(parsed, k=3)
        
        # Should route to mirror
        if decision.candidates:
            top_candidate = decision.candidates[0]
            assert top_candidate["protocol_id"] == "mirror"
    
    def test_confidence_thresholds(self):
        """Test confidence threshold routing decisions."""
        router = ProtocolRouter(self.test_config)
        router.catalog = self.test_protocols
        
        # Test high confidence (should route to single)
        parsed = ParsedQuery(
            normalized_text="leadership burden heavy weight carrying",
            stones_signals=["stewardship"],
            keywords=["leadership", "burden", "heavy", "weight", "carrying"],
            intents=["support"]
        )
        
        decision = router._route_keywords_only(parsed, k=3)
        
        # With high keyword overlap, should have high confidence
        if decision.confidence >= router.min_conf_single:
            assert decision.route == "single"
            assert len(decision.candidates) == 1
        
        # Test low confidence (should route to all)
        parsed = ParsedQuery(
            normalized_text="completely unrelated query about something else",
            stones_signals=[],
            keywords=["unrelated", "something", "else"],
            intents=[]
        )
        
        decision = router._route_keywords_only(parsed, k=3)
        
        # With no overlap, should have low confidence
        if decision.confidence < router.min_conf_triple:
            assert decision.route == "all"
            assert len(decision.candidates) == 0
    
    def test_jaccard_overlap(self):
        """Test Jaccard overlap calculation."""
        router = ProtocolRouter(self.test_config)
        
        # Test identical lists
        assert router._jaccard_overlap(["a", "b"], ["a", "b"]) == 1.0
        
        # Test no overlap
        assert router._jaccard_overlap(["a", "b"], ["c", "d"]) == 0.0
        
        # Test partial overlap
        assert router._jaccard_overlap(["a", "b"], ["b", "c"]) == 0.33  # 1/3
        
        # Test empty lists
        assert router._jaccard_overlap([], ["a", "b"]) == 0.0
        assert router._jaccard_overlap(["a", "b"], []) == 0.0
    
    def test_keyword_match(self):
        """Test keyword matching functionality."""
        router = ProtocolRouter(self.test_config)
        
        keywords = ["leadership", "heavy", "burden"]
        target_terms = ["leadership", "burden", "weight", "carrying"]
        
        score = router._keyword_match(keywords, target_terms)
        assert 0.0 <= score <= 1.0
        assert score > 0.0  # Should have some matches
        
        # Test no matches
        score = router._keyword_match(["xyz"], ["abc", "def"])
        assert score == 0.0


class TestRAGIntegration:
    """Test RAG adapter integration with router."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_config = {
            "fast": {
                "top_k": 20,
                "mmr_lambda": 0.5,
                "embed_model": "all-MiniLM-L6-v2"
            },
            "accurate": {
                "top_k_retrieve": 50,
                "top_k_rerank": 10,
                "cross_encoder": "cross-encoder/ms-marco-electra-base",
                "embed_model": "all-MiniLM-L6-v2"
            },
            "router": {
                "enabled": True,
                "k": 3,
                "min_conf_single": 0.45,
                "min_conf_double": 0.30,
                "min_conf_triple": 0.22,
                "weights": {
                    "embed": 0.6,
                    "stones": 0.2,
                    "keywords": 0.2
                }
            },
            "vector_store": {
                "provider": "faiss",
                "fast": {
                    "path": "/tmp/test_fast.faiss",
                    "meta": "/tmp/test_fast_meta.jsonl"
                },
                "accurate": {
                    "path": "/tmp/test_accurate.faiss",
                    "meta": "/tmp/test_accurate_meta.jsonl"
                }
            }
        }
    
    @patch('hallway.adapters.rag_adapter.load_store')
    def test_retrieve_with_router(self, mock_load_store):
        """Test retrieval with router enabled."""
        # Mock FAISS store
        mock_store = Mock()
        mock_store.embed_query.return_value = [0.1] * 384  # Mock embedding
        mock_store.search.return_value = [
            (0, 0.9), (1, 0.8), (2, 0.7), (3, 0.6), (4, 0.5)
        ]
        mock_store.get_meta.side_effect = lambda idx: {
            "doc": f"protocol_{idx % 3}",
            "chunk": idx,
            "text": f"Test text {idx}",
            "title": f"Protocol {idx % 3}"
        }
        mock_store._mmr_rerank.return_value = [
            (0, 0.9), (1, 0.8), (2, 0.7)
        ]
        mock_store.get_embedder_name.return_value = "all-MiniLM-L6-v2"
        
        mock_load_store.return_value = mock_store
        
        # Mock router
        with patch('hallway.adapters.rag_adapter.parse_query') as mock_parse, \
             patch('hallway.adapters.rag_adapter.route_query') as mock_route:
            
            mock_parse.return_value = ParsedQuery(
                normalized_text="leadership heavy burden",
                stones_signals=["stewardship"],
                keywords=["leadership", "heavy", "burden"],
                intents=["support"]
            )
            
            mock_route.return_value = RouteDecision(
                candidates=[{
                    "protocol_id": "leadership_carrying",
                    "title": "Leadership Carrying",
                    "score": 0.8
                }],
                confidence=0.8,
                route="single"
            )
            
            # Create RAG adapter
            adapter = RAGAdapter()
            adapter.config = self.test_config
            adapter.faiss_stores = {"fast": mock_store}
            
            # Test retrieval with router
            results = adapter._live_retrieve("leadership feels heavy", "fast", use_router=True)
            
            # Verify router was called
            mock_parse.assert_called_once()
            mock_route.assert_called_once()
            
            # Verify results
            assert len(results) > 0
            assert all("router_decision" in result for result in results)
            
            # Check router decision in results
            router_decision = results[0]["router_decision"]
            assert router_decision["route"] == "single"
            assert router_decision["confidence"] == 0.8
    
    @patch('hallway.adapters.rag_adapter.load_store')
    def test_retrieve_without_router(self, mock_load_store):
        """Test retrieval without router (use_router=False)."""
        # Mock FAISS store
        mock_store = Mock()
        mock_store.embed_query.return_value = [0.1] * 384
        mock_store.search.return_value = [(0, 0.9), (1, 0.8), (2, 0.7)]
        mock_store.get_meta.side_effect = lambda idx: {
            "doc": f"protocol_{idx}",
            "chunk": idx,
            "text": f"Test text {idx}",
            "title": f"Protocol {idx}"
        }
        mock_store._mmr_rerank.return_value = [(0, 0.9), (1, 0.8), (2, 0.7)]
        mock_store.get_embedder_name.return_value = "all-MiniLM-L6-v2"
        
        mock_load_store.return_value = mock_store
        
        # Create RAG adapter
        adapter = RAGAdapter()
        adapter.config = self.test_config
        adapter.faiss_stores = {"fast": mock_store}
        
        # Test retrieval without router
        results = adapter._live_retrieve("test query", "fast", use_router=False)
        
        # Verify results don't have router information
        assert len(results) > 0
        assert all("router_decision" not in result for result in results)
    
    @patch('hallway.adapters.rag_adapter.load_store')
    def test_router_fallback_on_error(self, mock_load_store):
        """Test that router errors fall back to global search."""
        # Mock FAISS store
        mock_store = Mock()
        mock_store.embed_query.return_value = [0.1] * 384
        mock_store.search.return_value = [(0, 0.9), (1, 0.8), (2, 0.7)]
        mock_store.get_meta.side_effect = lambda idx: {
            "doc": f"protocol_{idx}",
            "chunk": idx,
            "text": f"Test text {idx}",
            "title": f"Protocol {idx}"
        }
        mock_store._mmr_rerank.return_value = [(0, 0.9), (1, 0.8), (2, 0.7)]
        mock_store.get_embedder_name.return_value = "all-MiniLM-L6-v2"
        
        mock_load_store.return_value = mock_store
        
        # Mock router to raise exception
        with patch('hallway.adapters.rag_adapter.parse_query') as mock_parse:
            mock_parse.side_effect = Exception("Router error")
            
            # Create RAG adapter
            adapter = RAGAdapter()
            adapter.config = self.test_config
            adapter.faiss_stores = {"fast": mock_store}
            
            # Test retrieval with router error
            results = adapter._live_retrieve("test query", "fast", use_router=True)
            
            # Should still return results (fallback to global search)
            assert len(results) > 0
            assert all("router_decision" not in result for result in results)


class TestEndToEndRouting:
    """Test end-to-end routing scenarios."""
    
    def test_leadership_scenario(self):
        """Test end-to-end routing for leadership scenario."""
        config = {
            "router": {
                "enabled": True,
                "k": 3,
                "min_conf_single": 0.45,
                "min_conf_double": 0.30,
                "min_conf_triple": 0.22,
                "weights": {
                    "embed": 0.6,
                    "stones": 0.2,
                    "keywords": 0.2
                }
            }
        }
        
        # Create test protocols
        protocols = {
            "leadership_carrying": ProtocolEntry(
                protocol_id="leadership_carrying",
                title="The Leadership I'm Actually Carrying",
                short_title="Leadership Carrying",
                stones=["stewardship", "wholeness"],
                tags=["leadership", "burden", "weight"],
                fields=["leadership", "stewardship"],
                bridges=[],
                key_phrases=["hidden load", "leadership burden", "carrying weight"]
            ),
            "pace_gate": ProtocolEntry(
                protocol_id="pace_gate",
                title="Pace Gate",
                short_title="Pace Gate",
                stones=["speed", "trust"],
                tags=["pace", "rhythm"],
                fields=["pace", "rhythm"],
                bridges=[],
                key_phrases=["rushing", "pace adjustment"]
            )
        }
        
        router = ProtocolRouter(config)
        router.catalog = protocols
        
        # Test leadership query
        query = "leadership feels heavy / hidden load"
        parsed = router.parse_query(query)
        decision = router._route_keywords_only(parsed, k=3)
        
        # Should route to leadership_carrying
        assert decision.route in ["single", "double", "triple"]
        if decision.candidates:
            top_candidate = decision.candidates[0]
            assert top_candidate["protocol_id"] == "leadership_carrying"
    
    def test_pace_scenario(self):
        """Test end-to-end routing for pace scenario."""
        config = {
            "router": {
                "enabled": True,
                "k": 3,
                "min_conf_single": 0.45,
                "min_conf_double": 0.30,
                "min_conf_triple": 0.22,
                "weights": {
                    "embed": 0.6,
                    "stones": 0.2,
                    "keywords": 0.2
                }
            }
        }
        
        protocols = {
            "pace_gate": ProtocolEntry(
                protocol_id="pace_gate",
                title="Pace Gate",
                short_title="Pace Gate",
                stones=["speed", "trust"],
                tags=["pace", "rhythm", "speed"],
                fields=["pace", "rhythm"],
                bridges=[],
                key_phrases=["rushing", "pace adjustment", "rhythm", "speed control"]
            ),
            "leadership_carrying": ProtocolEntry(
                protocol_id="leadership_carrying",
                title="The Leadership I'm Actually Carrying",
                short_title="Leadership Carrying",
                stones=["stewardship", "wholeness"],
                tags=["leadership", "burden"],
                fields=["leadership", "stewardship"],
                bridges=[],
                key_phrases=["hidden load", "leadership burden"]
            )
        }
        
        router = ProtocolRouter(config)
        router.catalog = protocols
        
        # Test pace query
        query = "I'm rushing and losing trust / pace off"
        parsed = router.parse_query(query)
        decision = router._route_keywords_only(parsed, k=3)
        
        # Should route to pace_gate
        assert decision.route in ["single", "double", "triple"]
        if decision.candidates:
            top_candidate = decision.candidates[0]
            assert top_candidate["protocol_id"] == "pace_gate"
    
    def test_mirror_scenario(self):
        """Test end-to-end routing for mirror scenario."""
        config = {
            "router": {
                "enabled": True,
                "k": 3,
                "min_conf_single": 0.45,
                "min_conf_double": 0.30,
                "min_conf_triple": 0.22,
                "weights": {
                    "embed": 0.6,
                    "stones": 0.2,
                    "keywords": 0.2
                }
            }
        }
        
        protocols = {
            "mirror": ProtocolEntry(
                protocol_id="mirror",
                title="Mirror Protocol",
                short_title="Mirror",
                stones=["presence", "clarity"],
                tags=["reflection", "mirror", "clarity"],
                fields=["presence", "clarity"],
                bridges=[],
                key_phrases=["reflect back", "mirror words", "clear reflection", "presence"]
            ),
            "pace_gate": ProtocolEntry(
                protocol_id="pace_gate",
                title="Pace Gate",
                short_title="Pace Gate",
                stones=["speed", "trust"],
                tags=["pace", "rhythm"],
                fields=["pace", "rhythm"],
                bridges=[],
                key_phrases=["rushing", "pace adjustment"]
            )
        }
        
        router = ProtocolRouter(config)
        router.catalog = protocols
        
        # Test mirror query
        query = "reflect back my words clearly"
        parsed = router.parse_query(query)
        decision = router._route_keywords_only(parsed, k=3)
        
        # Should route to mirror
        assert decision.route in ["single", "double", "triple"]
        if decision.candidates:
            top_candidate = decision.candidates[0]
            assert top_candidate["protocol_id"] == "mirror"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
