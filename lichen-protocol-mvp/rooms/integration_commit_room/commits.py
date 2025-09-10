from typing import List, Dict, Any, Optional, Tuple
from .contract_types import Commitment, PaceState, DeclineReason, DeclineResponse


class CommitRecording:
    """Handles commitment recording with structure validation"""
    
    @staticmethod
    def validate_commitment_structure(payload: Any) -> Tuple[bool, Optional[List[Commitment]], Optional[DeclineResponse]]:
        """
        Validate that commitments are properly structured.
        Returns: (is_valid, commitments_list, decline_response)
        """
        if not payload:
            decline = DeclineResponse(
                reason=DeclineReason.INVALID_COMMITMENT_STRUCTURE,
                message="Commitments are required for closure",
                details="Payload is empty or missing",
                required_fields=["commitments"]
            )
            return False, None, decline
        
        if not isinstance(payload, dict):
            decline = DeclineResponse(
                reason=DeclineReason.INVALID_COMMITMENT_STRUCTURE,
                message="Commitments must be provided as structured data",
                details="Payload is not a dictionary",
                required_fields=["commitments"]
            )
            return False, None, decline
        
        if "commitments" not in payload:
            decline = DeclineResponse(
                reason=DeclineReason.INVALID_COMMITMENT_STRUCTURE,
                message="Commitments field is required",
                details="Payload must include 'commitments' field",
                required_fields=["commitments"]
            )
            return False, None, decline
        
        commitments_data = payload["commitments"]
        if not isinstance(commitments_data, list):
            decline = DeclineResponse(
                reason=DeclineReason.INVALID_COMMITMENT_STRUCTURE,
                message="Commitments must be provided as a list",
                details="Commitments field must be a list",
                required_fields=["commitments"]
            )
            return False, None, decline
        
        if not commitments_data:
            decline = DeclineResponse(
                reason=DeclineReason.INVALID_COMMITMENT_STRUCTURE,
                message="At least one commitment is required",
                details="Commitments list cannot be empty",
                required_fields=["commitments"]
            )
            return False, None, decline
        
        # Validate each commitment
        validated_commitments = []
        for i, commit_data in enumerate(commitments_data):
            is_valid, commitment, error = CommitRecording._validate_single_commitment(commit_data, i)
            if not is_valid:
                decline = DeclineResponse(
                    reason=DeclineReason.INVALID_COMMITMENT_STRUCTURE,
                    message=f"Invalid commitment at index {i}: {error}",
                    details=f"Commitment {i+1} failed validation",
                    required_fields=["text", "context", "pace_state", "session_ref"]
                )
                return False, None, decline
            validated_commitments.append(commitment)
        
        return True, validated_commitments, None
    
    @staticmethod
    def _validate_single_commitment(commit_data: Any, index: int) -> Tuple[bool, Optional[Commitment], Optional[str]]:
        """
        Validate a single commitment item.
        Returns: (is_valid, commitment_object, error_message)
        """
        if not isinstance(commit_data, dict):
            return False, None, "Commitment must be a dictionary"
        
        # Check required fields
        required_fields = ["text", "context", "pace_state", "session_ref"]
        missing_fields = []
        
        for field in required_fields:
            if field not in commit_data:
                missing_fields.append(field)
        
        if missing_fields:
            return False, None, f"Missing required fields: {', '.join(missing_fields)}"
        
        # Validate text field
        text = commit_data["text"]
        if not text or not isinstance(text, str) or len(text.strip()) < 3:
            return False, None, "Commitment text must be at least 3 characters"
        
        # Validate context field
        context = commit_data["context"]
        if not context or not isinstance(context, str) or len(context.strip()) < 2:
            return False, None, "Commitment context must be at least 2 characters"
        
        # Validate pace_state field
        pace_state_str = commit_data["pace_state"]
        try:
            pace_state = PaceState(pace_state_str)
        except ValueError:
            valid_states = [state.value for state in PaceState]
            return False, None, f"Invalid pace_state. Must be one of: {', '.join(valid_states)}"
        
        # Validate session_ref field
        session_ref = commit_data["session_ref"]
        if not session_ref or not isinstance(session_ref, str):
            return False, None, "Session reference must be a non-empty string"
        
        # Create commitment object
        commitment = Commitment(
            text=text.strip(),
            context=context.strip(),
            pace_state=pace_state,
            session_ref=session_ref,
            commitment_id=f"commit-{index}"
        )
        
        return True, commitment, None
    
    @staticmethod
    def format_commitments_summary(commitments: List[Commitment]) -> str:
        """Format commitments into a human-readable summary"""
        if not commitments:
            return "**No commitments recorded**"
        
        summary_parts = [
            "## Commitments Summary",
            f"**Total Commitments**: {len(commitments)}",
            ""
        ]
        
        for i, commitment in enumerate(commitments, 1):
            summary_parts.append(f"### Commitment {i}")
            summary_parts.append(f"**Text**: {commitment.text}")
            summary_parts.append(f"**Context**: {commitment.context}")
            summary_parts.append(f"**Pace**: {commitment.pace_state.value}")
            summary_parts.append(f"**Session Ref**: {commitment.session_ref}")
            summary_parts.append(f"**Timestamp**: {commitment.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            summary_parts.append("")
        
        return "\n".join(summary_parts)
    
    @staticmethod
    def validate_commitment_completeness(commitments: List[Commitment]) -> bool:
        """Check if commitments are complete for closure"""
        if not commitments:
            return False
        
        # Check that each commitment has all required fields
        for commitment in commitments:
            if not all([
                commitment.text,
                commitment.context,
                commitment.pace_state,
                commitment.session_ref
            ]):
                return False
        
        return True
    
    @staticmethod
    def get_commitment_requirements() -> List[str]:
        """Get list of required commitment fields"""
        return ["text", "context", "pace_state", "session_ref"]
    
    @staticmethod
    def get_commitment_statistics(commitments: List[Commitment]) -> Dict[str, Any]:
        """Get statistics about commitments"""
        if not commitments:
            return {
                "total": 0,
                "pace_distribution": {},
                "contexts": set()
            }
        
        pace_counts = {}
        contexts = set()
        
        for commitment in commitments:
            # Count pace states
            pace_value = commitment.pace_state.value
            pace_counts[pace_value] = pace_counts.get(pace_value, 0) + 1
            
            # Collect unique contexts
            contexts.add(commitment.context)
        
        return {
            "total": len(commitments),
            "pace_distribution": pace_counts,
            "contexts": list(contexts)
        }
