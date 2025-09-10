"""
Diagnostic Room Module
Implements the Diagnostic Room Protocol and Contract for Lichen Protocol Room Architecture (PRA)
"""

from rooms.diagnostic_room.diagnostic_room import DiagnosticRoom, run_diagnostic_room
from rooms.diagnostic_room.room_types import (
    DiagnosticRoomInput,
    DiagnosticRoomOutput,
    DiagnosticSignals,
    ReadinessState,
    ProtocolMapping
)

__all__ = [
    'DiagnosticRoom',
    'run_diagnostic_room',
    'DiagnosticRoomInput',
    'DiagnosticRoomOutput',
    'DiagnosticSignals',
    'ReadinessState',
    'ProtocolMapping'
]
