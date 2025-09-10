"""
Gate enforcement for the Hallway Protocol
Provides gate interface and coherence gate implementation
"""

from typing import Dict, Any, List, Tuple


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
            "exit_room"
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
        gates = {"coherence_gate": CoherenceGate()}
    
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
