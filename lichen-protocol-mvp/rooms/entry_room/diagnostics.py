"""
Diagnostics Module
Implements Diagnostics by Default theme from Entry Room Protocol
"""

from datetime import datetime
from typing import Optional
from .types import DiagnosticsPolicy, DiagnosticRecord, EntryRoomInput, EntryRoomContext, EntryRoomOutput


class DefaultDiagnosticsPolicy(DiagnosticsPolicy):
    """
    Captures diagnostics when enabled, respecting diagnostics_default setting.
    Returns diagnostic record or None if disabled.
    """
    
    async def capture_diagnostics(
        self,
        input_data: EntryRoomInput,
        interim: EntryRoomContext,
        output: EntryRoomOutput
    ) -> Optional[DiagnosticRecord]:
        """Capture diagnostic information when enabled"""
        # Check if diagnostics are enabled
        if not interim.diagnostics_enabled:
            return None
        
        # Capture basic diagnostic information
        diagnostics = DiagnosticRecord(
            timestamp=datetime.now().isoformat(),
            session_id=interim.session_id,
            room_id="entry_room"
        )
        
        # Add optional properties only if they have values
        tone = self._analyze_tone(input_data.payload)
        if tone:
            diagnostics.tone = tone
        
        residue = self._analyze_residue(input_data.payload)
        if residue:
            diagnostics.residue = residue
        
        readiness = self._analyze_readiness(input_data.payload, interim)
        if readiness:
            diagnostics.readiness = readiness
        
        return diagnostics
    
    def _analyze_tone(self, payload: any) -> Optional[str]:
        """Analyze tone based on text content"""
        if isinstance(payload, str):
            # Simple tone analysis based on text content
            text = payload.lower()
            
            if any(word in text for word in ['urgent', 'asap', 'quick']):
                return 'urgent'
            if any(word in text for word in ['calm', 'patient', 'gentle']):
                return 'calm'
            if any(word in text for word in ['excited', 'enthusiastic', 'great']):
                return 'excited'
            if any(word in text for word in ['worried', 'concerned', 'anxious']):
                return 'worried'
        
        return None
    
    def _analyze_residue(self, payload: any) -> Optional[str]:
        """Analyze for signs of previous interactions"""
        if isinstance(payload, str):
            text = payload.lower()
            
            # Look for signs of previous interactions or unresolved issues
            if any(word in text for word in ['still', 'again', 'still not']):
                return 'unresolved_previous'
            if any(word in text for word in ['tried', 'attempted', 'failed']):
                return 'previous_attempts'
        
        return None
    
    def _analyze_readiness(self, payload: any, ctx: EntryRoomContext) -> Optional[str]:
        """Analyze readiness based on context and payload"""
        # Analyze readiness based on context
        if ctx.pace_state in ["HOLD", "LATER"]:
            return 'not_ready'
        
        if isinstance(payload, str):
            text = payload.lower()
            
            if any(word in text for word in ['ready', 'let\'s go', 'start']):
                return 'ready'
            if any(word in text for word in ['wait', 'hold', 'later']):
                return 'deferring'
        
        return 'neutral'


class MinimalDiagnosticsPolicy(DiagnosticsPolicy):
    """Minimal diagnostics policy that captures only essential information"""
    
    async def capture_diagnostics(
        self,
        input_data: EntryRoomInput,
        interim: EntryRoomContext,
        output: EntryRoomOutput
    ) -> Optional[DiagnosticRecord]:
        """Capture minimal diagnostic information"""
        if not interim.diagnostics_enabled:
            return None
        
        return DiagnosticRecord(
            timestamp=datetime.now().isoformat(),
            session_id=interim.session_id,
            room_id="entry_room"
        )


class VerboseDiagnosticsPolicy(DiagnosticsPolicy):
    """Verbose diagnostics policy that captures detailed information"""
    
    async def capture_diagnostics(
        self,
        input_data: EntryRoomInput,
        interim: EntryRoomContext,
        output: EntryRoomOutput
    ) -> Optional[DiagnosticRecord]:
        """Capture verbose diagnostic information"""
        if not interim.diagnostics_enabled:
            return None
        
        base_diagnostics = DefaultDiagnosticsPolicy()
        diagnostics = await base_diagnostics.capture_diagnostics(input_data, interim, output)
        
        if diagnostics:
            # Could add additional verbose information here
            # diagnostics.input_type = type(input_data.payload).__name__
            # diagnostics.input_length = len(str(input_data.payload)) if isinstance(input_data.payload, str) else 0
            pass
        
        return diagnostics
