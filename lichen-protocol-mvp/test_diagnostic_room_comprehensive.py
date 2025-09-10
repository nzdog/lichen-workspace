#!/usr/bin/env python3
"""
Comprehensive test script for Diagnostic Room - tests all components
"""

import sys
import os

# Add the diagnostic_room directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'diagnostic_room'))

from rooms.diagnostic_room.room_types import DiagnosticRoomInput, DiagnosticRoomOutput, DiagnosticSignals, ProtocolMapping
from rooms.diagnostic_room.sensing import capture_tone_and_residue
from rooms.diagnostic_room.readiness import assess_readiness, readiness_to_action
from rooms.diagnostic_room.mapping import map_to_protocol
from rooms.diagnostic_room.capture import capture_diagnostics, format_display_text
from rooms.diagnostic_room.completion import append_fixed_marker

def test_capture_only_sensing():
    """Test capture-only sensing"""
    print("Testing capture-only sensing...")
    
    # Test with explicit payload
    payload = {
        'tone_label': 'explicit_tone',
        'residue_label': 'explicit_residue',
        'readiness_state': 'HOLD'
    }
    
    signals = capture_tone_and_residue(payload)
    assert signals.tone_label == 'explicit_tone'
    assert signals.residue_label == 'explicit_residue'
    assert signals.readiness_state == 'HOLD'
    print("✓ Explicit signals captured correctly")
    
    # Test with minimal payload
    payload = "Simple text"
    signals = capture_tone_and_residue(payload)
    assert signals.tone_label == "unspecified"
    assert signals.residue_label == "unspecified"
    assert signals.readiness_state == "NOW"
    print("✓ Defaults to unspecified correctly")
    
    # Test deterministic patterns
    payload = "I feel overwhelmed by this situation"
    signals = capture_tone_and_residue(payload)
    assert signals.tone_label == "overwhelm"
    print("✓ Deterministic tone detection works")
    
    payload = "I still have the same problem"
    signals = capture_tone_and_residue(payload)
    assert signals.residue_label == "unresolved_previous"
    print("✓ Deterministic residue detection works")

def test_readiness_tagging():
    """Test readiness assessment"""
    print("\nTesting readiness assessment...")
    
    # Test explicit readiness
    signals = DiagnosticSignals(
        tone_label="unspecified",
        residue_label="unspecified",
        readiness_state="LATER"
    )
    readiness = assess_readiness(signals)
    assert readiness == "LATER"
    print("✓ Explicit readiness respected")
    
    # Test tone-based readiness
    signals = DiagnosticSignals(
        tone_label="overwhelm",
        residue_label="unspecified",
        readiness_state="NOW"
    )
    readiness = assess_readiness(signals)
    assert readiness == "HOLD"
    print("✓ Tone-based readiness works")
    
    # Test all four states
    states = ["NOW", "HOLD", "LATER", "SOFT_HOLD"]
    for state in states:
        signals = DiagnosticSignals(
            tone_label="unspecified",
            residue_label="unspecified",
            readiness_state=state
        )
        readiness = assess_readiness(signals)
        assert readiness == state
    print("✓ All four readiness states supported")

def test_protocol_mapping():
    """Test protocol mapping"""
    print("\nTesting protocol mapping...")
    
    # Test tone-based mapping
    signals = DiagnosticSignals(
        tone_label="overwhelm",
        residue_label="unspecified",
        readiness_state="NOW"
    )
    mapping = map_to_protocol(signals)
    assert mapping.suggested_protocol_id == "resourcing_mini_walk"
    assert "overwhelm" in mapping.rationale
    print("✓ Tone-based mapping works")
    
    # Test residue-based mapping
    signals = DiagnosticSignals(
        tone_label="unspecified",
        residue_label="unresolved_previous",
        readiness_state="NOW"
    )
    mapping = map_to_protocol(signals)
    assert mapping.suggested_protocol_id == "integration_pause"
    assert "unresolved_previous" in mapping.rationale
    print("✓ Residue-based mapping works")
    
    # Test fixed template rationale
    signals = DiagnosticSignals(
        tone_label="urgency",
        residue_label="unspecified",
        readiness_state="NOW"
    )
    mapping = map_to_protocol(signals)
    assert "Tone: urgency →" in mapping.rationale
    assert mapping.rationale.endswith("Clearing for focus")
    print("✓ Fixed template rationale works")

def test_diagnostics_toggle():
    """Test diagnostics toggle"""
    print("\nTesting diagnostics toggle...")
    
    signals = DiagnosticSignals(
        tone_label="worry",
        residue_label="unspecified",
        readiness_state="HOLD"
    )
    
    mapping = ProtocolMapping(
        suggested_protocol_id="pacing_adjustment",
        rationale="Test rationale"
    )
    
    # Test enabled
    diagnostic_data = capture_diagnostics(signals, mapping, diagnostics_enabled=True)
    assert diagnostic_data is not None
    assert diagnostic_data["tone_label"] == "worry"
    assert diagnostic_data["readiness_state"] == "HOLD"
    assert diagnostic_data["suggested_protocol_id"] == "pacing_adjustment"
    print("✓ Diagnostics enabled captures data")
    
    # Test disabled
    diagnostic_data = capture_diagnostics(signals, mapping, diagnostics_enabled=False)
    assert diagnostic_data is None
    print("✓ Diagnostics disabled skips capture")

def test_completion_marker():
    """Test completion marker"""
    print("\nTesting completion marker...")
    
    text = "Sample diagnostic text"
    result = append_fixed_marker(text)
    assert result.endswith(" [[COMPLETE]]")
    assert result == "Sample diagnostic text [[COMPLETE]]"
    print("✓ Fixed marker appended correctly")
    
    # Test no variants
    assert result.count("[[COMPLETE]]") == 1
    print("✓ Only single marker used")

def test_integration():
    """Test full integration"""
    print("\nTesting full integration...")
    
    input_data = DiagnosticRoomInput(
        session_state_ref='integration-test',
        payload='I feel overwhelmed and still have unresolved issues'
    )
    
    # Test sensing
    signals = capture_tone_and_residue(input_data.payload)
    assert signals.tone_label == "overwhelm"
    assert signals.residue_label == "unresolved_previous"
    
    # Test readiness
    readiness = assess_readiness(signals)
    assert readiness in ["NOW", "HOLD", "LATER", "SOFT_HOLD"]
    
    # Test mapping
    mapping = map_to_protocol(signals)
    assert mapping.suggested_protocol_id in ["resourcing_mini_walk", "integration_pause"]
    
    # Test display text
    display_text = format_display_text(signals, mapping)
    final_text = append_fixed_marker(display_text)
    assert final_text.endswith(" [[COMPLETE]]")
    
    print("✓ Full integration works")

def main():
    """Run all tests"""
    print("Diagnostic Room Implementation Tests")
    print("=" * 50)
    
    try:
        test_capture_only_sensing()
        test_readiness_tagging()
        test_protocol_mapping()
        test_diagnostics_toggle()
        test_completion_marker()
        test_integration()
        
        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("The Diagnostic Room implementation is working correctly.")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
