"""
Rooms Module Index
Exports all room implementations and utilities
"""

# Entry Room
from .entry_room import EntryRoom, run_entry_room, EntryRoomConfig

# Entry Room Components
from .entry_room.reflection import VerbatimReflection
from .entry_room.gates import GateChain, GateChainConfig
from .entry_room.pace import DefaultPacePolicy, SimplePacePolicy, AdaptivePacePolicy
from .entry_room.consent import DefaultConsentPolicy, ExplicitConsentPolicy, GraduatedConsentPolicy
from .entry_room.diagnostics import DefaultDiagnosticsPolicy, MinimalDiagnosticsPolicy, VerboseDiagnosticsPolicy
from .entry_room.completion import DefaultCompletionPolicy, MinimalCompletionPolicy, VerboseCompletionPolicy, CustomCompletionPolicy

# Types
from .entry_room.types import (
    EntryRoomInput,
    EntryRoomOutput,
    EntryRoomContext,
    PaceState,
    GateResult,
    DiagnosticRecord,
    GateAdapter,
    PacePolicy,
    ConsentPolicy,
    DiagnosticsPolicy,
    CompletionPolicy,
    ReflectionPolicy
)

# Utilities
from .entry_room.pace import pace_state_to_next_action
from .entry_room.consent import generate_consent_request, is_consent_required
from .entry_room.completion import has_completion_marker, remove_completion_markers

__all__ = [
    # Entry Room
    'EntryRoom',
    'run_entry_room',
    'EntryRoomConfig',
    
    # Entry Room Components
    'VerbatimReflection',
    'GateChain',
    'GateChainConfig',
    'DefaultPacePolicy',
    'SimplePacePolicy',
    'AdaptivePacePolicy',
    'DefaultConsentPolicy',
    'ExplicitConsentPolicy',
    'GraduatedConsentPolicy',
    'DefaultDiagnosticsPolicy',
    'MinimalDiagnosticsPolicy',
    'VerboseDiagnosticsPolicy',
    'DefaultCompletionPolicy',
    'MinimalCompletionPolicy',
    'VerboseCompletionPolicy',
    'CustomCompletionPolicy',
    
    # Types
    'EntryRoomInput',
    'EntryRoomOutput',
    'EntryRoomContext',
    'PaceState',
    'GateResult',
    'DiagnosticRecord',
    'GateAdapter',
    'PacePolicy',
    'ConsentPolicy',
    'DiagnosticsPolicy',
    'CompletionPolicy',
    'ReflectionPolicy',
    
    # Utilities
    'pace_state_to_next_action',
    'generate_consent_request',
    'is_consent_required',
    'has_completion_marker',
    'remove_completion_markers'
]
