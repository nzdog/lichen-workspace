from typing import Dict, Any, Optional, List, Union
from .contract_types import (
    IntegrationCommitRoomInput, IntegrationCommitRoomOutput, RoomState,
    IntegrationData, Commitment, DeclineResponse
)
from .integration import IntegrationEnforcement
from .commits import CommitRecording
from .pace import PaceEnforcement
from .memory_write import MemoryWrite
from .completion import Completion


class IntegrationCommitRoom:
    """Main orchestrator for Integration & Commit Room operations"""
    
    def __init__(self):
        self.room_states: Dict[str, RoomState] = {}
        self.memory_write = MemoryWrite()
    
    def run_integration_commit_room(self, input_data: IntegrationCommitRoomInput) -> IntegrationCommitRoomOutput:
        """
        Main entry point for Integration & Commit Room operations.
        Orchestrates: integration → commit recording → pace enforcement → memory write → completion
        """
        try:
            # Parse input to determine operation
            operation = self._parse_input_operation(input_data)
            
            if operation == "integration":
                return self._handle_integration(input_data)
            elif operation == "commitments":
                return self._handle_commitments(input_data)
            elif operation == "complete":
                return self._handle_completion(input_data)
            elif operation == "status":
                return self._handle_status(input_data)
            else:
                return self._handle_default(input_data)
                
        except Exception as e:
            # Return structured error response
            error_text = f"Integration & Commit Room Error: {str(e)}"
            return IntegrationCommitRoomOutput(
                display_text=error_text,
                next_action="continue"
            )
    
    def _parse_input_operation(self, input_data: IntegrationCommitRoomInput) -> str:
        """Parse input to determine the operation type"""
        payload = input_data.payload
        
        if not payload:
            return "default"
        
        if isinstance(payload, dict):
            # Check for explicit operation
            if "operation" in payload:
                return payload["operation"]
            
            # Check for completion request
            if "complete" in payload:
                return "complete"
            
            # Check for status request
            if "status" in payload:
                return "status"
            
            # Check for integration data (even if incomplete)
            if "integration_notes" in payload or "session_context" in payload:
                return "integration"
            
            # Check for commitments
            if "commitments" in payload:
                return "commitments"
        
        return "default"
    
    def _handle_integration(self, input_data: IntegrationCommitRoomInput) -> IntegrationCommitRoomOutput:
        """Handle integration data capture"""
        # Get or create room state
        room_state = self._get_or_create_room_state(input_data.session_state_ref)
        
        # Validate integration presence
        is_valid, integration_data, decline_response = IntegrationEnforcement.validate_integration_presence(
            input_data.payload
        )
        
        if not is_valid:
            response_text = Completion.format_operation_result(
                "Integration Capture", False, decline_response.message, decline_response.details
            )
            response_text = Completion.append_completion_marker(response_text)
            
            return IntegrationCommitRoomOutput(
                display_text=response_text,
                next_action="continue"
            )
        
        # Validate integration quality
        is_quality_valid, quality_decline = IntegrationEnforcement.validate_integration_quality(integration_data)
        
        if not is_quality_valid:
            response_text = Completion.format_operation_result(
                "Integration Quality Check", False, quality_decline.message, quality_decline.details
            )
            response_text = Completion.append_completion_marker(response_text)
            
            return IntegrationCommitRoomOutput(
                display_text=response_text,
                next_action="continue"
            )
        
        # Store integration data
        room_state.integration_data = integration_data
        room_state.integration_captured = True
        
        # Format response
        integration_summary = IntegrationEnforcement.format_integration_summary(integration_data)
        response_text = f"# Integration Captured Successfully\n\n{integration_summary}"
        
        # Append completion marker
        response_text = Completion.append_completion_marker(response_text)
        
        return IntegrationCommitRoomOutput(
            display_text=response_text,
            next_action="continue"
        )
    
    def _handle_commitments(self, input_data: IntegrationCommitRoomInput) -> IntegrationCommitRoomOutput:
        """Handle commitment recording"""
        # Get room state
        room_state = self._get_or_create_room_state(input_data.session_state_ref)
        
        # Check if integration is captured first
        if not room_state.integration_captured:
            response_text = Completion.format_operation_result(
                "Commitment Recording", False,
                "Integration must be captured before commitments can be recorded",
                "Please provide integration data first"
            )
            response_text = Completion.append_completion_marker(response_text)
            
            return IntegrationCommitRoomOutput(
                display_text=response_text,
                next_action="continue"
            )
        
        # Validate commitment structure
        is_valid, commitments, decline_response = CommitRecording.validate_commitment_structure(
            input_data.payload
        )
        
        if not is_valid:
            response_text = Completion.format_operation_result(
                "Commitment Validation", False, decline_response.message, decline_response.details
            )
            response_text = Completion.append_completion_marker(response_text)
            
            return IntegrationCommitRoomOutput(
                display_text=response_text,
                next_action="continue"
            )
        
        # Store commitments
        room_state.commitments = commitments
        room_state.commitments_recorded = True
        
        # Validate pace states
        is_pace_valid, pace_decline = PaceEnforcement.validate_pace_states(commitments)
        
        if not is_pace_valid:
            response_text = Completion.format_operation_result(
                "Pace Validation", False, pace_decline.message, pace_decline.details
            )
            response_text = Completion.append_completion_marker(response_text)
            
            return IntegrationCommitRoomOutput(
                display_text=response_text,
                next_action="continue"
            )
        
        # Mark pace as enforced
        room_state.pace_enforced = True
        
        # Format response
        commitments_summary = CommitRecording.format_commitments_summary(commitments)
        pace_summary = PaceEnforcement.format_pace_summary(commitments)
        response_text = f"# Commitments Recorded Successfully\n\n{commitments_summary}\n\n{pace_summary}"
        
        # Append completion marker
        response_text = Completion.append_completion_marker(response_text)
        
        return IntegrationCommitRoomOutput(
            display_text=response_text,
            next_action="continue"
        )
    
    def _handle_completion(self, input_data: IntegrationCommitRoomInput) -> IntegrationCommitRoomOutput:
        """Handle room completion and memory write"""
        # Get room state
        room_state = self._get_or_create_room_state(input_data.session_state_ref)
        
        # Check if all requirements are met
        is_complete, missing_requirements = Completion.validate_completion_requirements(room_state)
        
        if not is_complete:
            response_text = Completion.format_operation_result(
                "Room Completion", False,
                "Cannot complete room - requirements not met",
                f"Missing: {', '.join(missing_requirements)}"
            )
            response_text = Completion.append_completion_marker(response_text)
            
            return IntegrationCommitRoomOutput(
                display_text=response_text,
                next_action="continue"
            )
        
        # Perform atomic memory write
        memory_result = self.memory_write.write_integration_and_commitments(
            input_data.session_state_ref,
            room_state.integration_data,
            room_state.commitments
        )
        
        if not memory_result.success:
            response_text = Completion.format_operation_result(
                "Memory Write", False,
                "Failed to write to memory",
                memory_result.error_details
            )
            response_text = Completion.append_completion_marker(response_text)
            
            return IntegrationCommitRoomOutput(
                display_text=response_text,
                next_action="continue"
            )
        
        # Mark memory as written
        room_state.memory_written = True
        
        # Format completion summary
        completion_summary = Completion.format_completion_summary(
            room_state, room_state.integration_data, room_state.commitments
        )
        
        # Append completion marker
        response_text = Completion.append_completion_marker(completion_summary)
        
        # Determine next action based on commitment pace states
        next_action = PaceEnforcement.get_room_next_action(room_state.commitments)
        
        return IntegrationCommitRoomOutput(
            display_text=response_text,
            next_action=next_action
        )
    
    def _handle_status(self, input_data: IntegrationCommitRoomInput) -> IntegrationCommitRoomOutput:
        """Handle status request"""
        # Get room state
        room_state = self._get_or_create_room_state(input_data.session_state_ref)
        
        # Get completion status
        completion_status = Completion.get_completion_status(room_state)
        progress_info = Completion.check_completion_progress(room_state)
        
        # Format status response
        status_parts = [
            "# Integration & Commit Room Status",
            "",
            completion_status,
            "",
            f"**Progress**: {progress_info['completion_percentage']:.1f}% complete",
            f"**Requirements Met**: {progress_info['completed_requirements']}/{progress_info['total_requirements']}",
            ""
        ]
        
        if room_state.integration_data:
            status_parts.append("## Integration Data")
            status_parts.append(f"**Session Context**: {room_state.integration_data.session_context}")
            status_parts.append(f"**Integration Notes**: {room_state.integration_data.integration_notes[:100]}...")
            status_parts.append("")
        
        if room_state.commitments:
            status_parts.append("## Commitments")
            status_parts.append(f"**Total**: {len(room_state.commitments)}")
            
            # Show pace distribution
            pace_distribution = PaceEnforcement.get_pace_distribution(room_state.commitments)
            for pace, count in pace_distribution.items():
                if count > 0:
                    status_parts.append(f"**{pace}**: {count}")
            status_parts.append("")
        
        status_parts.append("## Next Steps")
        if progress_info['can_terminate']:
            status_parts.append("✅ Room ready for completion")
        else:
            status_parts.append("⚠️ Complete missing requirements to finish")
        
        response_text = "\n".join(status_parts)
        
        # Append completion marker
        response_text = Completion.append_completion_marker(response_text)
        
        return IntegrationCommitRoomOutput(
            display_text=response_text,
            next_action="continue"
        )
    
    def _handle_default(self, input_data: IntegrationCommitRoomInput) -> IntegrationCommitRoomOutput:
        """Handle default case - show available operations"""
        room_state = self._get_or_create_room_state(input_data.session_state_ref)
        
        response_parts = [
            "# Integration & Commit Room - Available Operations",
            "",
            "## Current Status",
            f"**Session ID**: {input_data.session_state_ref}",
            f"**Integration Captured**: {'✅' if room_state.integration_captured else '❌'}",
            f"**Commitments Recorded**: {'✅' if room_state.commitments_recorded else '❌'}",
            f"**Pace Enforced**: {'✅' if room_state.pace_enforced else '❌'}",
            f"**Memory Written**: {'✅' if room_state.memory_written else '❌'}",
            "",
            "## Available Operations",
            "1. **Capture Integration**: Send data with integration_notes and session_context",
            "2. **Record Commitments**: Send data with commitments list (each with text, context, pace_state, session_ref)",
            "3. **Complete Room**: Send {'complete': true} to finalize and write to memory",
            "4. **Check Status**: Send {'status': true} to see current progress",
            "",
            "## Required Fields",
            "**Integration**: integration_notes, session_context",
            "**Commitments**: text, context, pace_state (NOW/HOLD/LATER/SOFT_HOLD), session_ref",
            "",
            "## Room Features",
            "✅ Integration capture enforced before closure",
            "✅ Commitment structure validation",
            "✅ Pace state enforcement on all commitments",
            "✅ Atomic memory write to prevent partial persistence"
        ]
        
        response_text = "\n".join(response_parts)
        
        # Append completion marker
        response_text = Completion.append_completion_marker(response_text)
        
        return IntegrationCommitRoomOutput(
            display_text=response_text,
            next_action="continue"
        )
    
    def _get_or_create_room_state(self, session_id: str) -> RoomState:
        """Get existing room state or create new one"""
        if session_id not in self.room_states:
            self.room_states[session_id] = RoomState()
        return self.room_states[session_id]
    
    def get_room_state(self, session_id: str) -> Optional[RoomState]:
        """Get room state for a session"""
        return self.room_states.get(session_id)
    
    def clear_room_state(self, session_id: str):
        """Clear room state for a session (for testing)"""
        if session_id in self.room_states:
            del self.room_states[session_id]


def run_integration_commit_room(input_data: Union[IntegrationCommitRoomInput, Dict[str, Any]]) -> Dict[str, Any]:
    """Standalone function to run Integration & Commit Room operations"""
    from rooms.integration_commit_room.contract_types import IntegrationCommitRoomInput
    from dataclasses import asdict
    inp = IntegrationCommitRoomInput.from_obj(input_data)
    room = IntegrationCommitRoom()
    result = room.run_integration_commit_room(inp)
    return asdict(result)
