"""
Step Diagnostics Module
Capture-only diagnostics for each walk step
"""

from typing import Dict, List, Optional
from .contract_types import StepDiagnostics, PaceState


class StepDiagnosticCapture:
    """Captures minimal structured diagnostics for each step"""
    
    @staticmethod
    def create_step_diagnostics(
        step_index: int,
        tone_label: Optional[str] = None,
        residue_label: Optional[str] = None,
        readiness_state: Optional[str] = None
    ) -> StepDiagnostics:
        """
        Create step diagnostics with defaults for missing values
        No interpretation, no sentiment analysis, no heuristics
        """
        return StepDiagnostics(
            step_index=step_index,
            tone_label=tone_label or "unspecified",
            residue_label=residue_label or "unspecified",
            readiness_state=readiness_state or PaceState.NOW.value
        )
    
    @staticmethod
    def validate_diagnostics(diagnostics: StepDiagnostics) -> bool:
        """Validate that diagnostics have required fields"""
        if not isinstance(diagnostics.step_index, int):
            return False
        if not isinstance(diagnostics.tone_label, str):
            return False
        if not isinstance(diagnostics.residue_label, str):
            return False
        if not isinstance(diagnostics.readiness_state, str):
            return False
        
        # Validate readiness state is a valid pace
        valid_paces = [p.value for p in PaceState]
        if diagnostics.readiness_state not in valid_paces:
            return False
        
        return True
    
    @staticmethod
    def format_diagnostics_summary(diagnostics_list: List[StepDiagnostics]) -> str:
        """Format diagnostics into a human-readable summary"""
        if not diagnostics_list:
            return "No diagnostics captured"
        
        summary_parts = []
        for diag in diagnostics_list:
            summary_parts.append(
                f"Step {diag.step_index}: "
                f"Tone: {diag.tone_label}, "
                f"Residue: {diag.residue_label}, "
                f"Readiness: {diag.readiness_state}"
            )
        
        return "\n".join(summary_parts)
    
    @staticmethod
    def get_diagnostics_by_step(
        diagnostics_list: List[StepDiagnostics],
        step_index: int
    ) -> Optional[StepDiagnostics]:
        """Get diagnostics for a specific step"""
        for diag in diagnostics_list:
            if diag.step_index == step_index:
                return diag
        return None
    
    @staticmethod
    def get_diagnostics_summary_stats(
        diagnostics_list: List[StepDiagnostics]
    ) -> Dict[str, any]:
        """Get summary statistics from diagnostics"""
        if not diagnostics_list:
            return {
                "total_steps": 0,
                "tone_distribution": {},
                "residue_distribution": {},
                "readiness_distribution": {}
            }
        
        tone_counts = {}
        residue_counts = {}
        readiness_counts = {}
        
        for diag in diagnostics_list:
            # Count tones
            tone_counts[diag.tone_label] = tone_counts.get(diag.tone_label, 0) + 1
            
            # Count residues
            residue_counts[diag.residue_label] = residue_counts.get(diag.residue_label, 0) + 1
            
            # Count readiness states
            readiness_counts[diag.readiness_state] = readiness_counts.get(diag.readiness_state, 0) + 1
        
        return {
            "total_steps": len(diagnostics_list),
            "tone_distribution": tone_counts,
            "residue_distribution": residue_counts,
            "readiness_distribution": readiness_counts
        }
    
    @staticmethod
    def export_diagnostics_to_dict(
        diagnostics_list: List[StepDiagnostics]
    ) -> List[Dict[str, any]]:
        """Export diagnostics to dictionary format for storage/transmission"""
        return [
            {
                "step_index": diag.step_index,
                "tone_label": diag.tone_label,
                "residue_label": diag.residue_label,
                "readiness_state": diag.readiness_state
            }
            for diag in diagnostics_list
        ]
