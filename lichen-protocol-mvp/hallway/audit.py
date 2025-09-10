"""
Audit utilities for the Hallway Protocol
Provides canonical JSON serialization and SHA256 hashing for audit trails
"""

import hashlib
import json
from typing import Any, Dict


def canonical_json(obj: Dict[str, Any]) -> str:
    """
    Ensure stable ordering and no whitespace variability for deterministic hashing.
    
    Args:
        obj: Dictionary to serialize
        
    Returns:
        Canonical JSON string with sorted keys and no whitespace
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_hex(payload: str) -> str:
    """
    Compute SHA256 hash of a string payload.
    
    Args:
        payload: String to hash
        
    Returns:
        Hexadecimal representation of the SHA256 hash
    """
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_step_hash(room_output_v01: Dict[str, Any]) -> str:
    """
    Compute the step hash for a room's v0.1 output.
    
    Args:
        room_output_v01: The legacy v0.1 room output dictionary
        
    Returns:
        Step hash in format "sha256:<hex_hash>"
    """
    payload = canonical_json(room_output_v01)
    return "sha256:" + sha256_hex(payload)


def build_audit_chain(steps: list) -> list:
    """
    Build the auditable hash chain from step results.
    
    Args:
        steps: List of StepResult objects
        
    Returns:
        List of step hashes in order
    """
    return [step["audit"]["step_hash"] for step in steps]
