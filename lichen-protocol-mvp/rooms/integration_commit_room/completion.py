from typing import List, Optional, Dict, Any
from .contract_types import IntegrationData, Commitment, RoomState


class Completion:
    """Handles completion enforcement and marker appending"""
    
    @staticmethod
    def append_completion_marker(text: str) -> str:
        """
        Append the fixed completion marker to display_text.
        Single marker only: [[COMPLETE]]
        No variants, no policies, no alternatives.
        """
        return text + " [[COMPLETE]]"
    
    @staticmethod
    def validate_completion_requirements(
        room_state: RoomState
    ) -> tuple[bool, List[str]]:
        """
        Validate that all completion requirements are met.
        Returns: (is_complete, list_of_missing_requirements)
        """
        missing_requirements = []
        
        # Check if integration was captured
        if not room_state.integration_captured:
            missing_requirements.append("Integration data not captured")
        
        # Check if commitments were recorded
        if not room_state.commitments_recorded:
            missing_requirements.append("Commitments not recorded")
        
        # Check if pace was enforced
        if not room_state.pace_enforced:
            missing_requirements.append("Pace states not enforced")
        
        # Check if we have actual data
        if not room_state.integration_data:
            missing_requirements.append("Integration data is missing")
        
        if not room_state.commitments:
            missing_requirements.append("Commitments list is empty")
        
        # Note: memory_written is set after successful memory write, not a prerequisite
        # for attempting completion
        
        is_complete = len(missing_requirements) == 0
        return is_complete, missing_requirements
    
    @staticmethod
    def get_completion_status(room_state: RoomState) -> str:
        """Get a human-readable completion status"""
        is_complete, missing_requirements = Completion.validate_completion_requirements(room_state)
        
        if is_complete:
            return "✅ Integration & Commit Room completion requirements satisfied"
        else:
            status_parts = ["⚠️ Integration & Commit Room completion requirements not satisfied:"]
            for req in missing_requirements:
                status_parts.append(f"  - {req}")
            return "\n".join(status_parts)
    
    @staticmethod
    def can_terminate_room(room_state: RoomState) -> bool:
        """Check if the room can be terminated"""
        is_complete, _ = Completion.validate_completion_requirements(room_state)
        return is_complete
    
    @staticmethod
    def format_completion_summary(
        room_state: RoomState,
        integration_data: IntegrationData,
        commitments: List[Commitment]
    ) -> str:
        """Format a comprehensive completion summary"""
        summary_parts = [
            "# Integration & Commit Room - Completion Summary",
            "",
            "## Room Status",
            f"**Integration Captured**: {'✅' if room_state.integration_captured else '❌'}",
            f"**Commitments Recorded**: {'✅' if room_state.commitments_recorded else '❌'}",
            f"**Pace Enforced**: {'✅' if room_state.pace_enforced else '❌'}",
            f"**Memory Written**: {'✅' if room_state.memory_written else '❌'}",
            ""
        ]
        
        # Add integration summary
        if integration_data:
            summary_parts.extend([
                "## Integration Data",
                f"**Session Context**: {integration_data.session_context}",
                f"**Integration Notes**: {integration_data.integration_notes}",
                ""
            ])
            
            if integration_data.key_insights:
                summary_parts.append("**Key Insights**:")
                for insight in integration_data.key_insights:
                    summary_parts.append(f"- {insight}")
                summary_parts.append("")
            
            if integration_data.shifts_noted:
                summary_parts.append("**Shifts Noted**:")
                for shift in integration_data.shifts_noted:
                    summary_parts.append(f"- {shift}")
                summary_parts.append("")
        
        # Add commitments summary
        if commitments:
            summary_parts.extend([
                "## Commitments",
                f"**Total Commitments**: {len(commitments)}",
                ""
            ])
            
            for i, commitment in enumerate(commitments, 1):
                summary_parts.append(f"### Commitment {i}")
                summary_parts.append(f"**Text**: {commitment.text}")
                summary_parts.append(f"**Context**: {commitment.context}")
                summary_parts.append(f"**Pace**: {commitment.pace_state.value}")
                summary_parts.append(f"**Session Ref**: {commitment.session_ref}")
                summary_parts.append("")
        
        # Add completion requirements status
        is_complete, missing_requirements = Completion.validate_completion_requirements(room_state)
        summary_parts.extend([
            "## Completion Requirements",
            f"**Status**: {'✅ Complete' if is_complete else '❌ Incomplete'}",
            ""
        ])
        
        if is_complete:
            summary_parts.append("All requirements satisfied - room can be terminated.")
        else:
            summary_parts.append("Missing requirements:")
            for req in missing_requirements:
                summary_parts.append(f"- {req}")
        
        return "\n".join(summary_parts)
    
    @staticmethod
    def format_operation_result(
        operation: str,
        success: bool,
        message: str,
        details: Optional[str] = None
    ) -> str:
        """Format the result of a room operation"""
        status_icon = "✅" if success else "❌"
        status_text = "Success" if success else "Failed"
        
        result_parts = [
            f"# {operation} Result",
            "",
            f"**Status**: {status_icon} {status_text}",
            f"**Message**: {message}"
        ]
        
        if details:
            result_parts.extend([
                "",
                "**Details**:",
                details
            ])
        
        result_parts.extend([
            "",
            "## Next Steps",
            "Integration & Commit Room is ready for the next operation."
        ])
        
        return "\n".join(result_parts)
    
    @staticmethod
    def get_completion_checklist() -> List[str]:
        """Get a checklist of completion requirements"""
        return [
            "Integration data captured and validated",
            "Commitments recorded with proper structure",
            "Pace states enforced on all commitments",
            "Memory write completed successfully",
            "All data properly formatted and stored"
        ]
    
    @staticmethod
    def check_completion_progress(room_state: RoomState) -> Dict[str, Any]:
        """Get detailed completion progress information"""
        total_requirements = 4
        completed_requirements = sum([
            room_state.integration_captured,
            room_state.commitments_recorded,
            room_state.pace_enforced,
            room_state.memory_written
        ])
        
        completion_percentage = (completed_requirements / total_requirements) * 100
        
        return {
            "total_requirements": total_requirements,
            "completed_requirements": completed_requirements,
            "completion_percentage": completion_percentage,
            "can_terminate": Completion.can_terminate_room(room_state),
            "missing_requirements": Completion.validate_completion_requirements(room_state)[1]
        }
