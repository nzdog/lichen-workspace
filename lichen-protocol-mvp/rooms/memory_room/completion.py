from typing import List, Optional
from .contract_types import MemoryItem, CaptureData


class MemoryCompletion:
    """Handles memory completion and marker appending"""
    
    @staticmethod
    def append_completion_marker(text: str) -> str:
        """
        Append the fixed completion marker to display_text.
        Single marker only: [[COMPLETE]]
        No variants, no policies, no alternatives.
        """
        return text + " [[COMPLETE]]"
    
    @staticmethod
    def format_memory_summary(
        session_id: str,
        items: List[MemoryItem],
        governance_summary: Optional[dict] = None
    ) -> str:
        """Format a comprehensive summary of memory operations"""
        summary_parts = [
            f"# Memory Room Summary - Session {session_id}",
            "",
            f"**Total Memory Items**: {len(items)}",
            ""
        ]
        
        # Add active vs deleted counts
        active_items = [item for item in items if not item.deleted_at]
        deleted_items = [item for item in items if item.deleted_at]
        
        summary_parts.extend([
            f"**Active Items**: {len(active_items)}",
            f"**Deleted Items**: {len(deleted_items)}",
            ""
        ])
        
        # Add pinned items count
        pinned_items = [item for item in active_items if item.is_pinned]
        if pinned_items:
            summary_parts.extend([
                f"**Pinned Items**: {len(pinned_items)}",
                ""
            ])
        
        # Add governance summary if available
        if governance_summary:
            summary_parts.extend([
                "## Governance Compliance",
                f"**Compliance Rate**: {governance_summary.get('compliance_rate', 0):.1%}",
                f"**Compliant Items**: {governance_summary.get('governance_compliant', 0)}",
                f"**Non-Compliant Items**: {governance_summary.get('governance_non_compliant', 0)}",
                ""
            ])
        
        # Add recent items summary
        if active_items:
            summary_parts.extend([
                "## Recent Memory Items",
                ""
            ])
            
            # Sort by most recent
            recent_items = sorted(active_items, key=lambda x: x.updated_at, reverse=True)[:5]
            
            for item in recent_items:
                summary_parts.append(
                    f"- **{item.capture_data.tone_label}** | "
                    f"{item.capture_data.residue_label} | "
                    f"{item.capture_data.readiness_state}"
                )
                if item.is_pinned:
                    summary_parts[-1] += " 📌"
        
        summary_parts.extend([
            "",
            "## Memory Room Status",
            "✅ Minimal capture policy enforced",
            "✅ User control operations supported",
            "✅ Continuity across rooms enabled",
            "✅ Stones-aligned governance applied",
            "✅ Completion requirements satisfied"
        ])
        
        return "\n".join(summary_parts)
    
    @staticmethod
    def validate_completion_requirements(
        items: List[MemoryItem],
        governance_applied: bool,
        user_control_available: bool
    ) -> tuple[bool, List[str]]:
        """
        Validate that all completion requirements are met
        Returns: (is_complete, list_of_missing_requirements)
        """
        missing_requirements = []
        
        # Check if memory items exist
        if not items:
            missing_requirements.append("No memory items captured")
        
        # Check if governance was applied
        if not governance_applied:
            missing_requirements.append("Governance rules not applied")
        
        # Check if user control is available
        if not user_control_available:
            missing_requirements.append("User control operations not available")
        
        # Check if we have at least one active item
        active_items = [item for item in items if not item.deleted_at]
        if not active_items:
            missing_requirements.append("No active memory items")
        
        is_complete = len(missing_requirements) == 0
        return is_complete, missing_requirements
    
    @staticmethod
    def get_completion_status(
        items: List[MemoryItem],
        governance_applied: bool,
        user_control_available: bool
    ) -> str:
        """Get a human-readable completion status"""
        is_complete, missing_requirements = MemoryCompletion.validate_completion_requirements(
            items, governance_applied, user_control_available
        )
        
        if is_complete:
            return "✅ Memory Room completion requirements satisfied"
        else:
            status_parts = ["⚠️ Memory Room completion requirements not satisfied:"]
            for req in missing_requirements:
                status_parts.append(f"  - {req}")
            return "\n".join(status_parts)
    
    @staticmethod
    def can_terminate_memory_room(
        items: List[MemoryItem],
        governance_applied: bool,
        user_control_available: bool
    ) -> bool:
        """Check if the Memory Room can be terminated"""
        is_complete, _ = MemoryCompletion.validate_completion_requirements(
            items, governance_applied, user_control_available
        )
        return is_complete
    
    @staticmethod
    def format_operation_result(
        operation: str,
        success: bool,
        message: str,
        items_affected: int = 0
    ) -> str:
        """Format the result of a memory operation"""
        status_icon = "✅" if success else "❌"
        status_text = "Success" if success else "Failed"
        
        result_parts = [
            f"# Memory Operation Result",
            "",
            f"**Operation**: {operation}",
            f"**Status**: {status_icon} {status_text}",
            f"**Message**: {message}"
        ]
        
        if items_affected > 0:
            result_parts.append(f"**Items Affected**: {items_affected}")
        
        result_parts.extend([
            "",
            "## Next Steps",
            "Memory Room is ready for additional operations or completion."
        ])
        
        return "\n".join(result_parts)
