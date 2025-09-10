"""
Sequencer Module
Enforces canonical order of protocol steps and prevents skipping/collapsing
"""

from typing import List, Optional, Tuple
from .contract_types import WalkStep, WalkState, WalkSession


class StepSequencer:
    """Manages step sequence and enforces canonical order"""
    
    def __init__(self, steps: List[WalkStep]):
        self.steps = steps
        self.current_index = 0
        self.total_steps = len(steps)
    
    def get_current_step(self) -> Optional[WalkStep]:
        """Get the current step without advancing"""
        if 0 <= self.current_index < self.total_steps:
            return self.steps[self.current_index]
        return None
    
    def can_advance(self) -> bool:
        """Check if we can advance to the next step"""
        return self.current_index < self.total_steps - 1
    
    def can_retreat(self) -> bool:
        """Check if we can retreat to the previous step"""
        return self.current_index > 0
    
    def advance_step(self) -> Tuple[bool, Optional[str]]:
        """
        Advance to next step if possible
        Returns: (success, error_message)
        """
        if not self.can_advance():
            return False, "Cannot advance: already at last step"
        
        self.current_index += 1
        return True, None
    
    def retreat_step(self) -> Tuple[bool, Optional[str]]:
        """
        Retreat to previous step if possible
        Returns: (success, error_message)
        """
        if not self.can_retreat():
            return False, "Cannot retreat: already at first step"
        
        self.current_index -= 1
        return True, None
    
    def jump_to_step(self, step_index: int) -> Tuple[bool, Optional[str]]:
        """
        Jump to specific step if valid
        Returns: (success, error_message)
        """
        if not (0 <= step_index < self.total_steps):
            return False, f"Invalid step index: {step_index}"
        
        self.current_index = step_index
        return True, None
    
    def get_step_progress(self) -> Tuple[int, int]:
        """Get current step number and total steps"""
        return self.current_index + 1, self.total_steps
    
    def is_complete(self) -> bool:
        """Check if all steps have been completed"""
        return self.current_index >= self.total_steps - 1
    
    def get_remaining_steps(self) -> int:
        """Get number of remaining steps"""
        return max(0, self.total_steps - self.current_index - 1)
    
    def get_step_by_index(self, index: int) -> Optional[WalkStep]:
        """Get step by index if valid"""
        if 0 <= index < self.total_steps:
            return self.steps[index]
        return None
    
    def validate_sequence_integrity(self) -> Tuple[bool, List[str]]:
        """
        Validate that the step sequence is intact
        Returns: (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for missing step indices
        expected_indices = set(range(self.total_steps))
        actual_indices = {step.step_index for step in self.steps}
        
        missing_indices = expected_indices - actual_indices
        if missing_indices:
            errors.append(f"Missing step indices: {missing_indices}")
        
        # Check for duplicate step indices
        duplicate_indices = [i for i in range(self.total_steps) 
                           if sum(1 for step in self.steps if step.step_index == i) > 1]
        if duplicate_indices:
            errors.append(f"Duplicate step indices: {duplicate_indices}")
        
        # Check for out-of-order step indices
        sorted_steps = sorted(self.steps, key=lambda x: x.step_index)
        if sorted_steps != self.steps:
            errors.append("Steps are not in canonical order")
        
        return len(errors) == 0, errors
