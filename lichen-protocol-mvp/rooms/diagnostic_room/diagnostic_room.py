"""
Diagnostic Room Implementation
Main orchestrator that implements the Diagnostic Room Protocol and Contract
"""

from typing import Optional, Union, Dict, Any
from rooms.diagnostic_room.room_types import DiagnosticRoomInput, DiagnosticRoomOutput
from rooms.diagnostic_room.sensing import capture_tone_and_residue
from rooms.diagnostic_room.readiness import assess_readiness, readiness_to_action
from rooms.diagnostic_room.mapping import map_to_protocol
from rooms.diagnostic_room.capture import capture_diagnostics, format_display_text
from rooms.diagnostic_room.completion import append_fixed_marker


class DiagnosticRoom:
    """Main Diagnostic Room class that orchestrates the protocol flow"""
    
    def __init__(self, diagnostics_enabled: bool = True):
        self.diagnostics_enabled = diagnostics_enabled
    
    def run_diagnostic_room(self, input_data: DiagnosticRoomInput) -> DiagnosticRoomOutput:
        """
        Main entry point that orchestrates the Diagnostic Room protocol.
        Implements: Sensing → Readiness Assessment → Protocol Mapping → Silent Capture → Completion
        """
        try:
            # 1. Sensing: Capture tone and residue signals
            signals = capture_tone_and_residue(input_data.payload)
            
            # 2. Readiness Assessment: Determine readiness state
            readiness = assess_readiness(signals)
            signals.readiness_state = readiness
            
            # 3. Protocol Mapping: Map signals to suggested protocol
            mapping = map_to_protocol(signals)
            
            # 4. Silent Capture: Record diagnostics if enabled
            diagnostic_data = capture_diagnostics(
                signals, 
                mapping, 
                self.diagnostics_enabled
            )
            
            # 5. Format display text
            display_text = format_display_text(signals, mapping)
            
            # 6. Completion: Add fixed marker
            display_text = append_fixed_marker(display_text)
            
            # 7. Determine next action (contract only allows "continue")
            next_action = "continue"
            
            return DiagnosticRoomOutput(
                display_text=display_text,
                next_action=next_action
            )
            
        except Exception as error:
            # Handle unexpected errors gracefully
            print(f"Diagnostic Room error: {error}")
            return DiagnosticRoomOutput(
                display_text=f"Diagnostic Room encountered an error: {str(error)}. [[COMPLETE]]",
                next_action="continue"
            )


def run_diagnostic_room(input_data: Union[DiagnosticRoomInput, Dict[str, Any]], diagnostics_enabled: bool = True) -> Dict[str, Any]:
    """Standalone function for external use"""
    from dataclasses import asdict
    from rooms.diagnostic_room.room_types import DiagnosticRoomInput
    inp = DiagnosticRoomInput.from_obj(input_data)
    room = DiagnosticRoom(diagnostics_enabled)
    result = room.run_diagnostic_room(inp)
    return asdict(result)
