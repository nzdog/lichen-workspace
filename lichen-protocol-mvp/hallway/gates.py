"""
Gate enforcement for the Hallway Protocol
Provides gate interface and coherence gate implementation
"""

import os
import json
from typing import Dict, Any, List, Tuple
from pathlib import Path


class GateDecision:
    """Represents a gate decision with allow/deny and metadata"""
    
    def __init__(self, gate: str, allow: bool, reason: str = "", details: Dict[str, Any] = None):
        self.gate = gate
        self.allow = allow
        self.reason = reason
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON serialization"""
        return {
            "gate": self.gate,
            "allow": self.allow,
            "reason": self.reason,
            "details": self.details
        }


class GateInterface:
    """Base interface for all gates"""
    
    def evaluate(self, room_id: str, session_state_ref: str, payload: Dict[str, Any] = None) -> GateDecision:
        """
        Evaluate whether a room should be allowed to proceed.
        
        Args:
            room_id: The room identifier
            session_state_ref: Reference to the session state
            payload: Optional room-specific payload
            
        Returns:
            GateDecision indicating allow/deny with reason
        """
        raise NotImplementedError("Subclasses must implement evaluate")


class CoherenceGate(GateInterface):
    """
    Coherence gate that performs basic validation checks.
    This is a deterministic gate that checks for basic coherence requirements.
    """
    
    def evaluate(self, room_id: str, session_state_ref: str, payload: Dict[str, Any] = None) -> GateDecision:
        """
        Evaluate basic coherence requirements.
        
        Args:
            room_id: The room identifier
            session_state_ref: Reference to the session state
            payload: Optional room-specific payload
            
        Returns:
            GateDecision indicating allow/deny with reason
        """
        # Check that session_state_ref is non-empty
        if not session_state_ref or not session_state_ref.strip():
            return GateDecision(
                gate="coherence_gate",
                allow=False,
                reason="session_state_ref is empty or missing",
                details={"room_id": room_id, "session_state_ref": session_state_ref}
            )
        
        # Check that room_id is valid
        valid_rooms = [
            "entry_room",
            "diagnostic_room", 
            "protocol_room",
            "walk_room",
            "memory_room",
            "integration_commit_room",
            "exit_room",
            "ai_room"
        ]
        
        if room_id not in valid_rooms:
            return GateDecision(
                gate="coherence_gate",
                allow=False,
                reason=f"room_id '{room_id}' is not in valid room list",
                details={"room_id": room_id, "valid_rooms": valid_rooms}
            )
        
        # All checks passed
        return GateDecision(
            gate="coherence_gate",
            allow=True,
            reason="All coherence checks passed",
            details={"room_id": room_id, "session_state_ref": session_state_ref}
        )


class GroundingGate(GateInterface):
    """
    Grounding gate that checks if RAG retrieval results meet minimum grounding thresholds.
    """
    
    def __init__(self, config_path: str = None):
        """Initialize grounding gate with configuration."""
        self.min_grounding = self._load_min_grounding(config_path)
        self.refusal_library = self._load_refusal_library()
    
    def _load_min_grounding(self, config_path: str = None) -> float:
        """Load minimum grounding threshold from config with env var override."""
        import os
        
        # Check for environment variable override first
        env_min_grounding = os.getenv("MIN_GROUNDING")
        if env_min_grounding:
            try:
                return float(env_min_grounding)
            except ValueError:
                pass  # Fall back to config file if env var is invalid
        
        if config_path is None:
            # Try multiple possible config paths
            config_paths = [
                "config/rag.yaml",
                "../config/rag.yaml", 
                "../../config/rag.yaml",
                "lichen-protocol-mvp/config/rag.yaml"
            ]
            
            for path in config_paths:
                if Path(path).exists():
                    config_path = path
                    break
        
        if config_path and Path(config_path).exists():
            try:
                import yaml
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                return config.get("limits", {}).get("min_grounding", 0.25)
            except Exception:
                pass
        
        # Default fallback
        return 0.25
    
    def _load_refusal_library(self) -> Dict[str, Any]:
        """Load refusal library for low grounding responses."""
        refusal_paths = [
            "contracts/gates/refusal_library.json",
            "../contracts/gates/refusal_library.json",
            "../../contracts/gates/refusal_library.json",
            "lichen-protocol-mvp/contracts/gates/refusal_library.json"
        ]
        
        for path in refusal_paths:
            if Path(path).exists():
                try:
                    with open(path, 'r') as f:
                        return json.load(f)
                except Exception:
                    continue
        
        # Default refusal library
        return {
            "gate_id": "refusal_library",
            "refusal_modes": {
                "low_grounding": "I can't offer that right now, but we can continue elsewhere.",
                "insufficient_support": "That's not something this system can walk with."
            }
        }
    
    def evaluate(self, room_id: str, session_state_ref: str, payload: Dict[str, Any] = None) -> GateDecision:
        """
        Evaluate grounding requirements for RAG results.
        
        Args:
            room_id: The room identifier
            session_state_ref: Reference to the session state
            payload: Optional room-specific payload containing RAG results
            
        Returns:
            GateDecision indicating allow/deny with reason
        """
        # Only check grounding for AI room or rooms with RAG results
        if room_id != "ai_room" and not (payload and "rag_context" in payload):
            return GateDecision(
                gate="grounding_gate",
                allow=True,
                reason="No RAG results to evaluate",
                details={"room_id": room_id}
            )
        
        # Extract grounding score from payload
        grounding_score = None
        if payload:
            # Check for grounding score in various possible locations
            if "grounding_score" in payload:
                grounding_score = payload["grounding_score"]
            elif "meta" in payload and "grounding_score_1to5" in payload["meta"]:
                # Convert 1-5 scale to 0-1 scale
                grounding_score = (payload["meta"]["grounding_score_1to5"] - 1) / 4.0
            elif "rag_context" in payload and "grounding_score" in payload["rag_context"]:
                grounding_score = payload["rag_context"]["grounding_score"]
        
        if grounding_score is None:
            # No grounding score available - allow but warn
            return GateDecision(
                gate="grounding_gate",
                allow=True,
                reason="No grounding score available for evaluation",
                details={"room_id": room_id, "warning": "grounding_score_missing"}
            )
        
        # Check against threshold
        if grounding_score < self.min_grounding:
            refusal_text = self.refusal_library.get("refusal_modes", {}).get(
                "low_grounding", 
                "I can't offer that right now, but we can continue elsewhere."
            )
            
            return GateDecision(
                gate="grounding_gate",
                allow=False,
                reason=f"Grounding score {grounding_score:.3f} below threshold {self.min_grounding}",
                details={
                    "room_id": room_id,
                    "grounding_score": grounding_score,
                    "min_threshold": self.min_grounding,
                    "refusal_text": refusal_text,
                    "refusal_mode": "low_grounding"
                }
            )
        
        return GateDecision(
            gate="grounding_gate",
            allow=True,
            reason=f"Grounding score {grounding_score:.3f} meets threshold {self.min_grounding}",
            details={"room_id": room_id, "grounding_score": grounding_score}
        )


def evaluate_gate_chain(
    gate_chain: List[str], 
    room_id: str, 
    session_state_ref: str, 
    payload: Dict[str, Any] = None,
    gates: Dict[str, GateInterface] = None
) -> Tuple[List[GateDecision], bool]:
    """
    Evaluate a chain of gates for a room.
    
    Args:
        gate_chain: List of gate names to evaluate
        room_id: The room identifier
        session_state_ref: Reference to the session state
        payload: Optional room-specific payload
        gates: Dictionary mapping gate names to gate implementations
        
    Returns:
        Tuple of (gate_decisions, all_passed)
    """
    if not gates:
        gates = {
            "coherence_gate": CoherenceGate(),
            "grounding_gate": GroundingGate()
        }
    
    gate_decisions = []
    all_passed = True
    
    for gate_name in gate_chain:
        if gate_name not in gates:
            # Unknown gate - deny by default
            decision = GateDecision(
                gate=gate_name,
                allow=False,
                reason=f"Gate '{gate_name}' not found in available gates",
                details={"available_gates": list(gates.keys())}
            )
            gate_decisions.append(decision)
            all_passed = False
            break
        
        gate = gates[gate_name]
        decision = gate.evaluate(room_id, session_state_ref, payload)
        gate_decisions.append(decision)
        
        if not decision.allow:
            all_passed = False
            break
    
    return gate_decisions, all_passed
