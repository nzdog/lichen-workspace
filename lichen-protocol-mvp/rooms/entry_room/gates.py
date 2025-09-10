"""
Gates Module
Orchestrates the gate chain: integrity_linter → plain_language_rewriter → stones_alignment_filter → coherence_gate
"""

from typing import Dict, Any
from .types import GateAdapter, GateResult, EntryRoomContext


class GateChainConfig:
    """Configuration for the gate chain"""
    
    def __init__(
        self,
        integrity_linter: GateAdapter,
        plain_language_rewriter: GateAdapter,
        stones_alignment_filter: GateAdapter,
        coherence_gate: GateAdapter
    ):
        self.integrity_linter = integrity_linter
        self.plain_language_rewriter = plain_language_rewriter
        self.stones_alignment_filter = stones_alignment_filter
        self.coherence_gate = coherence_gate


class GateChain:
    """Orchestrates the gate chain in order"""
    
    def __init__(self, config: GateChainConfig):
        self.gates = [
            config.integrity_linter,
            config.plain_language_rewriter,
            config.stones_alignment_filter,
            config.coherence_gate
        ]
    
    async def run_chain(self, text: str, ctx: EntryRoomContext) -> GateResult:
        """
        Runs the gate chain in order, halting on first failure.
        Returns structured decline if any gate fails.
        """
        current_text = text
        gate_names = ['integrity_linter', 'plain_language_rewriter', 'stones_alignment_filter', 'coherence_gate']
        
        for i, gate in enumerate(self.gates):
            gate_name = gate_names[i]
            
            try:
                result = await gate.run(current_text, ctx.__dict__)
                
                if not result.ok:
                    # Gate failed - return structured decline
                    return GateResult(
                        ok=False,
                        text=f"Gate {gate_name} declined: {', '.join(result.notes) if result.notes else 'Validation failed'}",
                        notes=[f"Gate: {gate_name}"] + (result.notes or [])
                    )
                
                # Gate passed - continue with processed text
                current_text = result.text
                
            except Exception as error:
                # Gate threw exception - return error decline
                return GateResult(
                    ok=False,
                    text=f"Gate {gate_name} error: {str(error)}",
                    notes=[f"Gate: {gate_name}", f"Error: {error}"]
                )
        
        # All gates passed
        return GateResult(
            ok=True,
            text=current_text,
            notes=['All gates passed successfully']
        )


# Default gate implementations (stubs for testing)
class StubIntegrityLinter(GateAdapter):
    """Stub implementation of integrity linter gate"""
    
    async def run(self, text: str, ctx: Dict[str, Any]) -> GateResult:
        # Stub implementation - always passes
        return GateResult(ok=True, text=text, notes=['Stub: integrity check passed'])


class StubPlainLanguageRewriter(GateAdapter):
    """Stub implementation of plain language rewriter gate"""
    
    async def run(self, text: str, ctx: Dict[str, Any]) -> GateResult:
        # Stub implementation - always passes
        return GateResult(ok=True, text=text, notes=['Stub: language rewrite passed'])


class StubStonesAlignmentFilter(GateAdapter):
    """Stub implementation of stones alignment filter gate"""
    
    async def run(self, text: str, ctx: Dict[str, Any]) -> GateResult:
        # Stub implementation - always passes
        return GateResult(ok=True, text=text, notes=['Stub: stones alignment passed'])


class StubCoherenceGate(GateAdapter):
    """Stub implementation of coherence gate"""
    
    async def run(self, text: str, ctx: Dict[str, Any]) -> GateResult:
        # Stub implementation - always passes
        return GateResult(ok=True, text=text, notes=['Stub: coherence check passed'])
