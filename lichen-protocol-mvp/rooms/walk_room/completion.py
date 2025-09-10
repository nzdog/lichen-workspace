"""
Completion Module
Enforces final closure and appends completion marker
"""

from typing import List, Optional
from .contract_types import CompletionPrompt, WalkStep


class WalkCompletion:
    """Handles walk completion and closure enforcement"""
    
    @staticmethod
    def create_completion_prompt(protocol_title: str, total_steps: int) -> CompletionPrompt:
        """Create a completion prompt for walk closure"""
        prompt_text = (
            f"Walk Complete: {protocol_title}\n\n"
            f"You have completed all {total_steps} steps of this protocol.\n"
            "Take a moment to reflect on your experience.\n\n"
            "Are you ready to conclude this walk?"
        )
        return CompletionPrompt(prompt_text=prompt_text, response_required=True)
    
    @staticmethod
    def format_walk_summary(
        protocol_title: str,
        steps: List[WalkStep],
        diagnostics_summary: str
    ) -> str:
        """Format a summary of the completed walk"""
        summary_parts = [
            f"# Walk Complete: {protocol_title}",
            "",
            f"**Steps Completed**: {len(steps)}",
            "",
            "## Step Summary"
        ]
        
        for step in steps:
            summary_parts.append(f"- **{step.title}**: {step.description}")
        
        summary_parts.extend([
            "",
            "## Diagnostics Summary",
            diagnostics_summary,
            "",
            "## Completion Status",
            "✅ All steps completed in canonical order",
            "✅ Pacing enforced at every step",
            "✅ Diagnostics captured across the walk",
            "✅ Closure confirmed before termination"
        ])
        
        return "\n".join(summary_parts)
    
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
        steps: List[WalkStep],
        current_step_index: int,
        diagnostics_captured: bool,
        completion_confirmed: bool
    ) -> tuple[bool, List[str]]:
        """
        Validate that all completion requirements are met
        Returns: (is_complete, list_of_missing_requirements)
        """
        missing_requirements = []
        
        # Check if all steps have been delivered
        if current_step_index < len(steps) - 1:
            missing_requirements.append("Not all steps have been delivered")
        
        # Check if diagnostics were captured
        if not diagnostics_captured:
            missing_requirements.append("Step diagnostics not captured")
        
        # Check if completion was confirmed
        if not completion_confirmed:
            missing_requirements.append("Completion not confirmed")
        
        is_complete = len(missing_requirements) == 0
        return is_complete, missing_requirements
    
    @staticmethod
    def get_completion_status(
        steps: List[WalkStep],
        current_step_index: int,
        diagnostics_captured: bool,
        completion_confirmed: bool
    ) -> str:
        """Get a human-readable completion status"""
        is_complete, missing_requirements = WalkCompletion.validate_completion_requirements(
            steps, current_step_index, diagnostics_captured, completion_confirmed
        )
        
        if is_complete:
            return "✅ Walk completion requirements satisfied"
        else:
            status_parts = ["⚠️ Walk completion requirements not satisfied:"]
            for req in missing_requirements:
                status_parts.append(f"  - {req}")
            return "\n".join(status_parts)
    
    @staticmethod
    def can_terminate_walk(
        steps: List[WalkStep],
        current_step_index: int,
        diagnostics_captured: bool,
        completion_confirmed: bool
    ) -> bool:
        """Check if the walk can be terminated"""
        is_complete, _ = WalkCompletion.validate_completion_requirements(
            steps, current_step_index, diagnostics_captured, completion_confirmed
        )
        return is_complete
