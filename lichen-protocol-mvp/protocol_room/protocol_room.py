"""
Protocol Room Implementation
Main orchestrator that implements the Protocol Room Protocol and Contract
"""

from typing import Optional, Dict, Any, List
from protocol_room.types import ProtocolRoomInput, ProtocolRoomOutput, ProtocolDepth, ProtocolText
from .canon import fetch_protocol_text, get_protocol_by_depth
from .depth import select_protocol_depth, format_depth_label, get_depth_description
from .mapping import map_scenario_to_protocol, get_scenario_mapping
from .integrity import validate_protocol_delivery
from .completion import append_fixed_marker


class ProtocolRoom:
    """Main Protocol Room class that orchestrates the protocol flow"""
    
    def __init__(self):
        """Initialize Protocol Room with default settings"""
        pass
    
    def run_protocol_room(self, input_data: ProtocolRoomInput) -> ProtocolRoomOutput:
        """
        Main entry point that orchestrates the Protocol Room protocol.
        Implements: Canon Fidelity → Depth Selection → Scenario Mapping → Integrity Gate → Completion
        """
        try:
            # Extract input parameters
            payload = input_data.payload or {}
            
            # 1. Determine protocol ID (from explicit request or scenario mapping)
            protocol_id = self._determine_protocol_id(payload)
            if not protocol_id:
                return self._create_error_output("No protocol ID specified and no scenario mapping found")
            
            # 2. Determine protocol depth
            depth = self._determine_protocol_depth(payload)
            
            # 3. Fetch protocol text from canon (exact, no edits)
            protocol_text = self._fetch_protocol_text(protocol_id, depth)
            if not protocol_text:
                return self._create_error_output(f"Protocol '{protocol_id}' not found in canon")
            
            # 4. Run integrity gate checks
            integrity_result = validate_protocol_delivery(protocol_text)
            if not integrity_result.passed:
                return self._create_decline_output(integrity_result.notes)
            
            # 5. Format display text
            display_text = self._format_protocol_display(protocol_id, depth, protocol_text)
            
            # 6. Add completion marker
            display_text = append_fixed_marker(display_text)
            
            return ProtocolRoomOutput(
                display_text=display_text,
                next_action="continue"
            )
            
        except Exception as error:
            # Handle unexpected errors gracefully
            print(f"Protocol Room error: {error}")
            return self._create_error_output(f"Protocol Room encountered an error: {str(error)}")
    
    def _determine_protocol_id(self, payload: Dict[str, Any]) -> Optional[str]:
        """Determine which protocol to serve"""
        # Check for explicit protocol ID
        if 'protocol_id' in payload and payload['protocol_id']:
            return payload['protocol_id']
        
        # Check for scenario mapping
        if 'scenario' in payload and payload['scenario']:
            return map_scenario_to_protocol(payload['scenario'])
        
        # Check for diagnostic signals that might suggest a protocol
        if 'suggested_protocol_id' in payload and payload['suggested_protocol_id']:
            return payload['suggested_protocol_id']
        
        return None
    
    def _determine_protocol_depth(self, payload: Dict[str, Any]) -> ProtocolDepth:
        """Determine protocol depth based on input"""
        requested_depth = payload.get('depth')
        readiness_level = payload.get('readiness_level')
        time_available = payload.get('time_available')
        
        return select_protocol_depth(
            requested_depth=requested_depth,
            readiness_level=readiness_level,
            time_available=time_available
        )
    
    def _fetch_protocol_text(self, protocol_id: str, depth: ProtocolDepth) -> Optional[str]:
        """Fetch protocol text from canon (exact, no edits)"""
        return get_protocol_by_depth(protocol_id, depth)
    
    def _format_protocol_display(self, protocol_id: str, depth: ProtocolDepth, protocol_text: str) -> str:
        """Format protocol for display"""
        depth_label = format_depth_label(depth)
        depth_description = get_depth_description(depth)
        
        # Get protocol metadata
        protocol = fetch_protocol_text(protocol_id)
        title = protocol.title if protocol else protocol_id
        description = protocol.description if protocol else ""
        
        # Format display
        lines = [
            f"# {title}",
            f"**{depth_label}** - {depth_description}",
            "",
            description,
            "",
            "---",
            "",
            protocol_text
        ]
        
        return "\n".join(lines)
    
    def _create_error_output(self, error_message: str) -> ProtocolRoomOutput:
        """Create error output with completion marker"""
        display_text = f"Protocol Room Error: {error_message}"
        display_text = append_fixed_marker(display_text)
        
        return ProtocolRoomOutput(
            display_text=display_text,
            next_action="continue"
        )
    
    def _create_decline_output(self, notes: List[str]) -> ProtocolRoomOutput:
        """Create decline output when integrity gate fails"""
        display_text = "Protocol Room: Integrity Gate Failed\n\n"
        display_text += "The requested protocol did not pass integrity checks:\n"
        for note in notes:
            display_text += f"• {note}\n"
        display_text += "\nPlease contact support or try a different protocol."
        
        display_text = append_fixed_marker(display_text)
        
        return ProtocolRoomOutput(
            display_text=display_text,
            next_action="continue"
        )


def run_protocol_room(input_data: ProtocolRoomInput) -> ProtocolRoomOutput:
    """Standalone function for external use"""
    room = ProtocolRoom()
    return room.run_protocol_room(input_data)
