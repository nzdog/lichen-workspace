"""
Entry Room Implementation
Main orchestrator that implements the Entry Room Protocol and Contract
"""

import asyncio
from typing import Optional, Dict, Any, Union
from rooms.entry_room.types import (
    EntryRoomInput,
    EntryRoomOutput,
    EntryRoomContext,
    PaceState,
    GateResult
)
from rooms.entry_room.reflection import VerbatimReflection
from rooms.entry_room.gates import GateChain, GateChainConfig, StubIntegrityLinter, StubPlainLanguageRewriter, StubStonesAlignmentFilter, StubCoherenceGate
from rooms.entry_room.pace import PacePolicy, pace_state_to_next_action, DefaultPacePolicy
from rooms.entry_room.consent import ConsentPolicy, DefaultConsentPolicy
from rooms.entry_room.diagnostics import DiagnosticsPolicy, DefaultDiagnosticsPolicy
from rooms.entry_room.completion import CompletionPolicy, DefaultCompletionPolicy


class EntryRoomConfig:
    """Configuration for Entry Room policies"""
    
    def __init__(
        self,
        reflection: Optional[VerbatimReflection] = None,
        gates: Optional[GateChainConfig] = None,
        pace: Optional[PacePolicy] = None,
        consent: Optional[ConsentPolicy] = None,
        diagnostics: Optional[DiagnosticsPolicy] = None,
        completion: Optional[CompletionPolicy] = None,
        diagnostics_default: bool = True
    ):
        self.reflection = reflection
        self.gates = gates
        self.pace = pace
        self.consent = consent
        self.diagnostics = diagnostics
        self.completion = completion
        self.diagnostics_default = diagnostics_default


class EntryRoom:
    """Main Entry Room class that orchestrates the protocol flow"""
    
    def __init__(self, config: Optional[EntryRoomConfig] = None):
        if config is None:
            config = EntryRoomConfig()
        
        # Initialize with defaults or provided implementations
        self.reflection = config.reflection or VerbatimReflection()
        self.gate_chain = GateChain(config.gates or self._create_default_gate_config())
        self.pace_policy = config.pace or self._create_default_pace_policy()
        self.consent_policy = config.consent or self._create_default_consent_policy()
        self.diagnostics_policy = config.diagnostics or self._create_default_diagnostics_policy()
        self.completion_policy = config.completion or self._create_default_completion_policy()
        self.diagnostics_default = config.diagnostics_default
    
    async def run_entry_room(self, input_data: Union[EntryRoomInput, Dict[str, Any]]) -> EntryRoomOutput:
        """
        Main entry point that orchestrates the Entry Room protocol.
        Implements: Faithful Reflection → Pre-Gate Chain → Pace Setting → Consent Anchor → Diagnostics → Completion Prompt → Output
        """
        try:
            # Convert dict input to EntryRoomInput if needed
            if isinstance(input_data, dict):
                input_data = EntryRoomInput(
                    session_state_ref=input_data.get("session_state_ref", ""),
                    payload=input_data.get("payload")
                )
            
            # 1. Faithful Reflection: Mirror input exactly
            reflected_ideas = self.reflection.reflect_verbatim(input_data.payload)
            display_text = '\n'.join(reflected_ideas)
            
            # 2. Pre-Gate Chain: Run gates in order
            gate_result = await self._run_gate_chain(display_text, input_data)
            if not gate_result.ok:
                # Gate failed - return decline with hold action
                return EntryRoomOutput(
                    display_text=gate_result.text,
                    next_action="hold"
                )
            display_text = gate_result.text
            
            # 3. Pace Setting: Determine session pacing
            pace_state = await self._set_pace(input_data)
            next_action = pace_state_to_next_action(pace_state)
            
            # 4. Consent Anchor: Require explicit consent
            consent_result = await self._enforce_consent(input_data, pace_state)
            if consent_result != "YES":
                # Consent not granted - return consent request
                return EntryRoomOutput(
                    display_text=self._generate_consent_request(consent_result),
                    next_action="hold" if consent_result == "HOLD" else "later"
                )
            
            # 5. Diagnostics: Capture diagnostic information
            output = EntryRoomOutput(
                display_text=display_text,
                next_action=next_action
            )
            
            # Only capture diagnostics if enabled
            if self.diagnostics_default:
                await self._capture_diagnostics(input_data, pace_state, output)
            
            # 6. Completion Prompt: Add completion marker
            output.display_text = self.completion_policy.append_completion_marker(output.display_text)
            
            return output
            
        except Exception as error:
            # Handle unexpected errors gracefully
            print(f"Entry Room error: {error}")
            return EntryRoomOutput(
                display_text=f"Entry Room encountered an error: {str(error)}. Please try again.",
                next_action="hold"
            )
    
    async def _run_gate_chain(self, text: str, input_data: EntryRoomInput) -> GateResult:
        """Run the gate chain with proper context"""
        context = EntryRoomContext(
            session_id=input_data.session_state_ref,
            pace_state="NOW",
            consent_granted=False,
            diagnostics_enabled=self.diagnostics_default
        )
        
        return await self.gate_chain.run_chain(text, context)
    
    async def _set_pace(self, input_data: EntryRoomInput) -> PaceState:
        """Set the pace for the session"""
        context = EntryRoomContext(
            session_id=input_data.session_state_ref,
            pace_state="NOW",
            consent_granted=False,
            diagnostics_enabled=self.diagnostics_default
        )
        
        return await self.pace_policy.apply_pace_gate(context)
    
    async def _enforce_consent(self, input_data: EntryRoomInput, pace_state: PaceState) -> str:
        """Enforce explicit consent before proceeding"""
        # Check for consent in the payload
        consent_granted = False
        if isinstance(input_data.payload, dict) and input_data.payload.get("consent") == "YES":
            consent_granted = True
        
        context = EntryRoomContext(
            session_id=input_data.session_state_ref,
            pace_state=pace_state,
            consent_granted=consent_granted,
            diagnostics_enabled=self.diagnostics_default
        )
        
        return await self.consent_policy.enforce_consent(context)
    
    async def _capture_diagnostics(
        self,
        input_data: EntryRoomInput,
        pace_state: PaceState,
        output: EntryRoomOutput
    ) -> None:
        """Capture diagnostic information"""
        try:
            context = EntryRoomContext(
                session_id=input_data.session_state_ref,
                pace_state=pace_state,
                consent_granted=True,
                diagnostics_enabled=True
            )
            
            await self.diagnostics_policy.capture_diagnostics(input_data, context, output)
        except Exception as error:
            # Diagnostics failure should not break the main flow
            print(f"Diagnostics capture failed: {error}")
    
    def _generate_consent_request(self, consent_result: str) -> str:
        """Generate appropriate consent request message"""
        if consent_result == "HOLD":
            return "Before we proceed, I need your explicit consent to continue. Please confirm that you're ready to proceed with this session."
        else:
            return "It seems you'd prefer to continue later. Please let me know when you're ready to proceed."
    
    # Default implementations
    def _create_default_gate_config(self) -> GateChainConfig:
        """Create default gate configuration with stub implementations"""
        return GateChainConfig(
            integrity_linter=StubIntegrityLinter(),
            plain_language_rewriter=StubPlainLanguageRewriter(),
            stones_alignment_filter=StubStonesAlignmentFilter(),
            coherence_gate=StubCoherenceGate()
        )
    
    def _create_default_pace_policy(self) -> PacePolicy:
        """Create default pace policy"""
        return DefaultPacePolicy()
    
    def _create_default_consent_policy(self) -> ConsentPolicy:
        """Create default consent policy"""
        return DefaultConsentPolicy()
    
    def _create_default_diagnostics_policy(self) -> DiagnosticsPolicy:
        """Create default diagnostics policy"""
        return DefaultDiagnosticsPolicy()
    
    def _create_default_completion_policy(self) -> CompletionPolicy:
        """Create default completion policy"""
        return DefaultCompletionPolicy()


async def run_entry_room(input_data: Union[EntryRoomInput, Dict[str, Any]], config: Optional[EntryRoomConfig] = None) -> Dict[str, Any]:
    """Standalone function for external use"""
    from dataclasses import asdict
    room = EntryRoom(config)
    result = await room.run_entry_room(input_data)
    return asdict(result)
