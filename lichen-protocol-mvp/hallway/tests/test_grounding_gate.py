"""
Tests for grounding gate functionality.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from ..gates import GroundingGate, GateDecision


class TestGroundingGate:
    """Test grounding gate functionality."""
    
    def test_grounding_gate_initialization(self):
        """Test grounding gate initializes with default values."""
        gate = GroundingGate()
        assert gate.min_grounding == 0.25
        assert "gate_id" in gate.refusal_library
    
    def test_grounding_gate_with_config(self):
        """Test grounding gate loads config correctly."""
        config_content = """
limits:
  min_grounding: 0.5
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            gate = GroundingGate(config_path)
            assert gate.min_grounding == 0.5
        finally:
            os.unlink(config_path)
    
    def test_grounding_gate_skips_non_ai_room(self):
        """Test grounding gate skips evaluation for non-AI rooms."""
        gate = GroundingGate()
        
        decision = gate.evaluate("diagnostic_room", "test_session", {})
        
        assert decision.allow is True
        assert decision.reason == "No RAG results to evaluate"
        assert decision.gate == "grounding_gate"
    
    def test_grounding_gate_allows_high_grounding(self):
        """Test grounding gate allows results above threshold."""
        gate = GroundingGate()
        
        payload = {
            "grounding_score": 0.8,
            "rag_context": {"query": "test query"}
        }
        
        decision = gate.evaluate("ai_room", "test_session", payload)
        
        assert decision.allow is True
        assert "meets threshold" in decision.reason
        assert decision.details["grounding_score"] == 0.8
    
    def test_grounding_gate_denies_low_grounding(self):
        """Test grounding gate denies results below threshold."""
        gate = GroundingGate()
        
        payload = {
            "grounding_score": 0.1,  # Below 0.25 threshold
            "rag_context": {"query": "test query"}
        }
        
        decision = gate.evaluate("ai_room", "test_session", payload)
        
        assert decision.allow is False
        assert "below threshold" in decision.reason
        assert decision.details["grounding_score"] == 0.1
        assert decision.details["min_threshold"] == 0.25
        assert "refusal_text" in decision.details
        assert decision.details["refusal_mode"] == "low_grounding"
    
    def test_grounding_gate_handles_missing_score(self):
        """Test grounding gate handles missing grounding score."""
        gate = GroundingGate()
        
        payload = {
            "rag_context": {"query": "test query"}
        }
        
        decision = gate.evaluate("ai_room", "test_session", payload)
        
        assert decision.allow is True
        assert "No grounding score available" in decision.reason
        assert decision.details["warning"] == "grounding_score_missing"
    
    def test_grounding_gate_converts_1to5_scale(self):
        """Test grounding gate converts 1-5 scale to 0-1 scale."""
        gate = GroundingGate()
        
        payload = {
            "meta": {"grounding_score_1to5": 3},  # Should become 0.5
            "rag_context": {"query": "test query"}
        }
        
        decision = gate.evaluate("ai_room", "test_session", payload)
        
        assert decision.allow is True
        assert decision.details["grounding_score"] == 0.5
    
    def test_grounding_gate_denies_1to5_scale_low(self):
        """Test grounding gate denies low 1-5 scale scores."""
        gate = GroundingGate()
        
        payload = {
            "meta": {"grounding_score_1to5": 1},  # Should become 0.0
            "rag_context": {"query": "test query"}
        }
        
        decision = gate.evaluate("ai_room", "test_session", payload)
        
        assert decision.allow is False
        assert decision.details["grounding_score"] == 0.0
    
    def test_grounding_gate_with_rag_context_score(self):
        """Test grounding gate extracts score from rag_context."""
        gate = GroundingGate()
        
        payload = {
            "rag_context": {
                "query": "test query",
                "grounding_score": 0.3
            }
        }
        
        decision = gate.evaluate("ai_room", "test_session", payload)
        
        assert decision.allow is True
        assert decision.details["grounding_score"] == 0.3
    
    def test_grounding_gate_custom_threshold(self):
        """Test grounding gate with custom threshold."""
        gate = GroundingGate()
        gate.min_grounding = 0.8  # Set high threshold
        
        payload = {
            "grounding_score": 0.7,  # Below 0.8 threshold
            "rag_context": {"query": "test query"}
        }
        
        decision = gate.evaluate("ai_room", "test_session", payload)
        
        assert decision.allow is False
        assert decision.details["min_threshold"] == 0.8


class TestGroundingGateIntegration:
    """Test grounding gate integration with gate chain."""
    
    def test_gate_chain_includes_grounding_gate(self):
        """Test that gate chain includes grounding gate by default."""
        from ..gates import evaluate_gate_chain
        
        # Use a valid room that coherence gate will accept
        gate_decisions, all_passed = evaluate_gate_chain(
            ["coherence_gate", "grounding_gate"],
            "entry_room",  # Valid room
            "test_session",
            {"grounding_score": 0.8}
        )
        
        assert len(gate_decisions) == 2
        assert gate_decisions[0].gate == "coherence_gate"
        assert gate_decisions[1].gate == "grounding_gate"
        assert all_passed is True
    
    def test_gate_chain_fails_on_low_grounding(self):
        """Test that gate chain fails when grounding is too low."""
        from ..gates import evaluate_gate_chain
        
        # Use ai_room to trigger grounding gate evaluation
        gate_decisions, all_passed = evaluate_gate_chain(
            ["coherence_gate", "grounding_gate"],
            "ai_room",  # This will trigger grounding gate
            "test_session",
            {"grounding_score": 0.1}
        )
        
        assert len(gate_decisions) == 2
        assert gate_decisions[0].allow is True  # coherence_gate passes
        assert gate_decisions[1].allow is False  # grounding_gate fails
        assert all_passed is False
