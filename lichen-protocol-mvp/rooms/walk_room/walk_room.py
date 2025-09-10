"""
Walk Room Module
Main orchestrator for protocol walk execution with sequence enforcement, pacing, and diagnostics
"""

from typing import Optional, Dict, Any, List, Tuple, Union
from .contract_types import (
    WalkRoomInput, WalkRoomOutput, WalkStep, WalkState, 
    PaceState, StepDiagnostics, ProtocolStructure, WalkSession
)
from .sequencer import StepSequencer
from .pacing import PaceGovernor
from .step_diag import StepDiagnosticCapture
from .completion import WalkCompletion


class WalkRoom:
    """Main orchestrator for Walk Room protocol execution"""
    
    def __init__(self):
        self.sessions: Dict[str, WalkSession] = {}
        self.protocol_structures: Dict[str, ProtocolStructure] = {}
    
    def run_walk_room(self, input_data: WalkRoomInput) -> WalkRoomOutput:
        """
        Main entry point for Walk Room execution
        Handles the full walk flow: sequence → pace → diagnostics → output → closure
        """
        try:
            # Parse input and determine action
            action = self._parse_input_action(input_data)
            
            if action == "start_walk":
                return self._start_walk(input_data)
            elif action == "get_current_step":
                return self._get_current_step(input_data)
            elif action == "advance_step":
                return self._advance_step(input_data)
            elif action == "set_pace":
                return self._set_pace(input_data)
            elif action == "confirm_completion":
                return self._confirm_completion(input_data)
            elif action == "get_walk_status":
                return self._get_walk_status(input_data)
            else:
                return self._create_error_output("Unknown action requested")
                
        except Exception as e:
            return self._create_error_output(f"Walk Room error: {str(e)}")
    
    def _parse_input_action(self, input_data: WalkRoomInput) -> str:
        """Parse input to determine requested action"""
        payload = input_data.payload or {}
        
        if isinstance(payload, dict):
            if "action" in payload:
                return payload["action"]
            elif "protocol_id" in payload and "steps" in payload:
                return "start_walk"
            elif "pace" in payload:
                return "set_pace"
            elif "confirm_completion" in payload:
                return "confirm_completion"
            elif "get_status" in payload:
                return "get_walk_status"
        
        return "get_current_step"  # Default action
    
    def _start_walk(self, input_data: WalkRoomInput) -> WalkRoomOutput:
        """Start a new protocol walk"""
        payload = input_data.payload or {}
        
        if not isinstance(payload, dict) or "protocol_id" not in payload:
            return self._create_error_output("Missing protocol_id in payload")
        
        protocol_id = payload["protocol_id"]
        steps_data = payload.get("steps", [])
        
        # Create protocol structure
        steps = []
        for i, step_data in enumerate(steps_data):
            if isinstance(step_data, dict):
                step = WalkStep(
                    step_index=i,
                    title=step_data.get("title", f"Step {i+1}"),
                    content=step_data.get("content", ""),
                    description=step_data.get("description", ""),
                    estimated_time=step_data.get("estimated_time")
                )
                steps.append(step)
        
        if not steps:
            return self._create_error_output("No valid steps provided")
        
        # Create completion prompt
        completion_prompt = WalkCompletion.create_completion_prompt(
            payload.get("title", protocol_id), len(steps)
        )
        
        # Create protocol structure
        protocol_structure = ProtocolStructure(
            protocol_id=protocol_id,
            title=payload.get("title", protocol_id),
            description=payload.get("description", ""),
            steps=steps,
            completion_prompt=completion_prompt
        )
        
        # Store protocol structure
        self.protocol_structures[protocol_id] = protocol_structure
        
        # Create walk session
        session = WalkSession(
            current_step_index=0,
            walk_state=WalkState.PENDING,
            steps=steps,
            diagnostics=[],
            completion_confirmed=False,
            protocol_id=protocol_id
        )
        
        self.sessions[input_data.session_state_ref] = session
        
        # Return first step
        return self._get_current_step(input_data)
    
    def _get_current_step(self, input_data: WalkRoomInput) -> WalkRoomOutput:
        """Get the current step for the session"""
        session = self._get_session(input_data.session_state_ref)
        if not session:
            return self._create_error_output("No active walk session")
        
        if session.walk_state == WalkState.COMPLETED:
            return self._handle_walk_completion(session)
        
        current_step = session.steps[session.current_step_index]
        
        # Format step output
        step_text = self._format_step_output(current_step, session)
        
        return WalkRoomOutput(
            display_text=step_text,
            next_action="continue"
        )
    
    def _advance_step(self, input_data: WalkRoomInput) -> WalkRoomOutput:
        """Advance to the next step if possible"""
        session = self._get_session(input_data.session_state_ref)
        if not session:
            return self._create_error_output("No active walk session")
        
        if session.walk_state == WalkState.COMPLETED:
            return self._handle_walk_completion(session)
        
        # Check if we can advance
        if session.current_step_index >= len(session.steps) - 1:
            return self._create_error_output("Cannot advance: already at last step")
        
        # Check if pace has been set for current step
        if not self._has_diagnostics_for_step(session, session.current_step_index):
            return self._create_error_output("Cannot advance: pace must be set for current step before advancing")
        
        # Advance to next step
        session.current_step_index += 1
        session.walk_state = WalkState.IN_STEP
        
        # Return new current step
        return self._get_current_step(input_data)
    
    def _set_pace(self, input_data: WalkRoomInput) -> WalkRoomOutput:
        """Set pace for current step"""
        payload = input_data.payload or {}
        if not isinstance(payload, dict) or "pace" not in payload:
            return self._create_error_output("Missing pace in payload")
        
        pace = payload["pace"]
        if not PaceGovernor.validate_pace_state(pace):
            return self._create_error_output(f"Invalid pace state: {pace}")
        
        session = self._get_session(input_data.session_state_ref)
        if not session:
            return self._create_error_output("No active walk session")
        
        # Capture diagnostics with the specified pace
        self._capture_step_diagnostics(
            session, 
            session.current_step_index,
            readiness_state=pace
        )
        
        # Determine next action based on pace
        next_action = PaceGovernor.map_pace_to_action(pace)
        
        # Format step output with pace information
        current_step = session.steps[session.current_step_index]
        step_text = self._format_step_output(current_step, session, pace)
        
        return WalkRoomOutput(
            display_text=step_text,
            next_action=next_action
        )
    
    def _confirm_completion(self, input_data: WalkRoomInput) -> WalkRoomOutput:
        """Confirm walk completion"""
        session = self._get_session(input_data.session_state_ref)
        if not session:
            return self._create_error_output("No active walk session")
        
        # Check if all steps are complete
        if session.current_step_index < len(session.steps) - 1:
            return self._create_error_output("Cannot complete: not all steps delivered")
        
        # Mark completion as confirmed
        session.completion_confirmed = True
        session.walk_state = WalkState.COMPLETED
        
        # Return completion summary
        return self._handle_walk_completion(session)
    
    def _get_walk_status(self, input_data: WalkRoomInput) -> WalkRoomOutput:
        """Get current walk status"""
        session = self._get_session(input_data.session_state_ref)
        if not session:
            return self._create_error_output("No active walk session")
        
        status_text = self._format_walk_status(session)
        
        return WalkRoomOutput(
            display_text=status_text,
            next_action="continue"
        )
    
    def _handle_walk_completion(self, session: WalkSession) -> WalkRoomOutput:
        """Handle walk completion and return final output"""
        # Format walk summary
        diagnostics_summary = StepDiagnosticCapture.format_diagnostics_summary(
            session.diagnostics
        )
        
        summary_text = WalkCompletion.format_walk_summary(
            session.protocol_id,
            session.steps,
            diagnostics_summary
        )
        
        # Append completion marker
        final_text = WalkCompletion.append_completion_marker(summary_text)
        
        return WalkRoomOutput(
            display_text=final_text,
            next_action="continue"
        )
    
    def _get_session(self, session_ref: str) -> Optional[WalkSession]:
        """Get walk session by reference"""
        return self.sessions.get(session_ref)
    
    def _has_diagnostics_for_step(self, session: WalkSession, step_index: int) -> bool:
        """Check if diagnostics exist for a specific step"""
        return any(diag.step_index == step_index for diag in session.diagnostics)
    
    def _capture_step_diagnostics(
        self, 
        session: WalkSession, 
        step_index: int,
        tone_label: Optional[str] = None,
        residue_label: Optional[str] = None,
        readiness_state: Optional[str] = None
    ):
        """Capture diagnostics for a specific step"""
        diagnostics = StepDiagnosticCapture.create_step_diagnostics(
            step_index, tone_label, residue_label, readiness_state
        )
        
        # Remove existing diagnostics for this step if they exist
        session.diagnostics = [
            d for d in session.diagnostics if d.step_index != step_index
        ]
        
        session.diagnostics.append(diagnostics)
    
    def _format_step_output(
        self, 
        step: WalkStep, 
        session: WalkSession,
        pace: Optional[str] = None
    ) -> str:
        """Format step output with pacing information"""
        current_step_num, total_steps = session.current_step_index + 1, len(session.steps)
        
        output_parts = [
            f"# {step.title}",
            f"**Step {current_step_num} of {total_steps}**",
            "",
            step.description,
            ""
        ]
        
        if step.content:
            output_parts.extend([
                "## Content",
                step.content,
                ""
            ])
        
        if step.estimated_time:
            output_parts.append(f"**Estimated Time**: {step.estimated_time} minutes")
        
        if pace:
            output_parts.extend([
                "",
                f"**Current Pace**: {pace}",
                PaceGovernor.get_pace_guidance(pace)
            ])
        else:
            output_parts.extend([
                "",
                "**Pace Required**: Please set your pace for this step",
                "Options: NOW, HOLD, LATER, SOFT_HOLD"
            ])
        
        return "\n".join(output_parts)
    
    def _format_walk_status(self, session: WalkSession) -> str:
        """Format walk status information"""
        current_step_num, total_steps = session.current_step_index + 1, len(session.steps)
        
        status_parts = [
            f"# Walk Status: {session.protocol_id}",
            f"**Current Step**: {current_step_num} of {total_steps}",
            f"**Walk State**: {session.walk_state.value}",
            f"**Steps Completed**: {len(session.diagnostics)}",
            f"**Completion Confirmed**: {session.completion_confirmed}",
            ""
        ]
        
        if session.diagnostics:
            status_parts.extend([
                "## Recent Diagnostics",
                StepDiagnosticCapture.format_diagnostics_summary(session.diagnostics[-3:])
            ])
        
        return "\n".join(status_parts)
    
    def _create_error_output(self, error_message: str) -> WalkRoomOutput:
        """Create error output with structured message"""
        error_text = f"Walk Room Error: {error_message}"
        return WalkRoomOutput(
            display_text=error_text,
            next_action="continue"
        )


def run_walk_room(input_data: Union[WalkRoomInput, Dict[str, Any]]) -> Dict[str, Any]:
    """Standalone function to run Walk Room"""
    from rooms.walk_room.contract_types import WalkRoomInput
    from dataclasses import asdict
    inp = WalkRoomInput.from_obj(input_data)
    room = WalkRoom()
    result = room.run_walk_room(inp)
    return asdict(result)
