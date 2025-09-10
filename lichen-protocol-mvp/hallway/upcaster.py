"""
Upcaster for the Hallway Protocol
Transforms v0.1 room outputs into v0.2 StepResult envelopes
"""

from typing import Optional, Dict, Any, List
from .audit import compute_step_hash, canonical_json, sha256_hex


def upcast_v01_to_v02(
    room_id: str,
    room_output_v01: Dict[str, Any],
    *,
    status: str,
    gate_decisions: List[Dict[str, Any]],
    prev_hash: Optional[str] = None,
    diagnostics_digest: Optional[str] = None,
    room_contract_version: str = "0.1.0"
) -> Dict[str, Any]:
    """
    Transform a v0.1 room output into a v0.2 StepResult envelope.
    
    Args:
        room_id: The room identifier
        room_output_v01: The legacy v0.1 room output dictionary
        status: "ok" or "decline" as determined by hallway
        gate_decisions: List of GateDecision-like dicts
        prev_hash: Previous step's audit hash (or None for first)
        diagnostics_digest: Precomputed sha256 or None
        room_contract_version: Version of the room's contract
        
    Returns:
        Dict validating against StepResult in the Hallway v0.2 schema
    """
    # Compute step hash over the legacy room output
    step_hash = compute_step_hash(room_output_v01)
    
    # Build the audit object
    audit = {
        "step_hash": step_hash,
        "prev_hash": prev_hash,
        "room_contract_version": room_contract_version
    }
    
    # Build the invariants object
    invariants = {
        "deterministic": True,
        "no_partial_write": True
    }
    
    # Build the decline object (null unless status == "decline")
    decline = None
    if status == "decline":
        decline = {
            "reason": "gate_denied_or_room_decline",
            "message": "See gate_decisions and data for details",
            "details": {}
        }
    
    # Construct the v0.2 StepResult envelope
    step_result = {
        "contract_version": "0.2.0",
        "room_id": room_id,
        "status": status,
        "data": room_output_v01,  # Legacy output verbatim
        "invariants": invariants,
        "gate_decisions": gate_decisions,
        "diagnostics_digest": diagnostics_digest if diagnostics_digest is not None else "sha256:" + sha256_hex(canonical_json(room_output_v01)),
        "audit": audit,
        "decline": decline
    }
    
    return step_result


def downcast_v02_to_v01(step_result_v02: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract the original v0.1 room output from a v0.2 StepResult envelope.
    
    Args:
        step_result_v02: The v0.2 StepResult envelope
        
    Returns:
        The original v0.1 room output
    """
    return step_result_v02["data"]


def verify_roundtrip(
    room_output_v01: Dict[str, Any],
    step_result_v02: Dict[str, Any]
) -> bool:
    """
    Verify that upcasting then downcasting returns the original payload.
    
    Args:
        room_output_v01: Original v0.1 room output
        step_result_v02: Upcasted v0.2 StepResult
        
    Returns:
        True if roundtrip is successful (byte-for-byte equal in canonical JSON)
    """
    from .audit import canonical_json
    
    # Extract the data field
    extracted_data = downcast_v02_to_v01(step_result_v02)
    
    # Compare canonical JSON representations
    original_canonical = canonical_json(room_output_v01)
    extracted_canonical = canonical_json(extracted_data)
    
    return original_canonical == extracted_canonical


def map_room_output_to_v02(room_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map room output shape to v0.2 StepResult fields.
    
    Args:
        room_output: The room's output dictionary
        
    Returns:
        Mapped output with v0.2 field names
    """
    mapped = {}
    
    # Map display_text to output.text if present
    if "display_text" in room_output:
        mapped["text"] = room_output["display_text"]
    
    # Map next_action to output.next_action if present
    if "next_action" in room_output:
        mapped["next_action"] = room_output["next_action"]
    
    # Handle decline objects
    if "_decline_reason" in room_output:
        mapped["decline"] = {
            "reason": room_output["_decline_reason"],
            "ok": False,
            "details": room_output.get("_error_details", {})
        }
    
    # Copy any other fields
    for key, value in room_output.items():
        if key not in ["display_text", "next_action", "_decline_reason", "_error_details"]:
            mapped[key] = value
    
    return mapped


def is_room_decline(room_output: Dict[str, Any]) -> bool:
    """
    Check if a room output indicates a decline.
    
    Args:
        room_output: The room's output dictionary
        
    Returns:
        True if the output indicates a decline
    """
    return (
        "_decline_reason" in room_output or
        room_output.get("next_action") == "hold" or
        room_output.get("next_action") == "later"
    )
