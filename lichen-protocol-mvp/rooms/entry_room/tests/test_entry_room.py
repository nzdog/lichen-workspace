"""
Entry Room Unit Tests
Tests all behavioral invariants and edge cases using pytest
"""

import pytest
import asyncio
from typing import List, Dict, Any
from rooms.entry_room.types import (
    EntryRoomInput,
    EntryRoomOutput,
    PaceState,
    GateResult,
    EntryRoomContext
)
from rooms.entry_room.entry_room import EntryRoom, EntryRoomConfig, run_entry_room
from rooms.entry_room.reflection import VerbatimReflection
from rooms.entry_room.gates import GateChainConfig
from rooms.entry_room.pace import PacePolicy
from rooms.entry_room.consent import ConsentPolicy
from rooms.entry_room.diagnostics import DiagnosticsPolicy
from rooms.entry_room.completion import CompletionPolicy


# Mock implementations for testing
class MockGateAdapter:
    """Mock gate adapter for testing"""
    
    def __init__(
        self,
        name: str,
        should_pass: bool = True,
        output_text: str = None,
        notes: List[str] = None
    ):
        self.name = name
        self.should_pass = should_pass
        self.output_text = output_text
        self.notes = notes or []
    
    async def run(self, text: str, ctx: Dict[str, Any]) -> GateResult:
        """Mock gate execution"""
        if not self.should_pass:
            return GateResult(
                ok=False,
                text=f"Gate {self.name} failed",
                notes=self.notes or [f"Mock failure in {self.name}"]
            )
        
        return GateResult(
            ok=True,
            text=self.output_text or text,
            notes=self.notes or [f"Mock success in {self.name}"]
        )


class MockPacePolicy(PacePolicy):
    """Mock pace policy for testing"""
    
    def __init__(self, return_pace: PaceState = "NOW"):
        self.return_pace = return_pace
    
    async def apply_pace_gate(self, ctx: EntryRoomContext) -> PaceState:
        """Mock pace determination"""
        return self.return_pace


class MockConsentPolicy(ConsentPolicy):
    """Mock consent policy for testing"""
    
    def __init__(self, return_consent: str = "YES"):
        self.return_consent = return_consent
    
    async def enforce_consent(self, ctx: EntryRoomContext) -> str:
        """Mock consent enforcement - ignores context and returns configured value"""
        return self.return_consent


class MockDiagnosticsPolicy(DiagnosticsPolicy):
    """Mock diagnostics policy for testing"""
    
    def __init__(self):
        self.captured_diagnostics = []
    
    async def capture_diagnostics(
        self,
        input_data: EntryRoomInput,
        interim: EntryRoomContext,
        output: EntryRoomOutput
    ) -> Any:
        """Mock diagnostic capture"""
        self.captured_diagnostics.append({
            'input': input_data,
            'interim': interim,
            'output': output
        })
        return {
            'timestamp': '2024-01-01T00:00:00',
            'session_id': interim.session_id,
            'room_id': 'entry_room'
        }


class MockCompletionPolicy(CompletionPolicy):
    """Mock completion policy for testing"""
    
    def append_completion_marker(self, text: str) -> str:
        """Mock completion marker addition"""
        return text + '\n[✓ TEST COMPLETE]'


class TestEntryRoom:
    """Test suite for Entry Room implementation"""
    
    @pytest.fixture
    def sample_input(self):
        """Sample input for testing"""
        return EntryRoomInput(
            session_state_ref='test-session-123',
            payload='Hello, I have multiple ideas. First idea. Second idea.'
        )
    
    @pytest.fixture
    def mock_gates(self):
        """Mock gate configuration"""
        return GateChainConfig(
            integrity_linter=MockGateAdapter('integrity_linter'),
            plain_language_rewriter=MockGateAdapter('plain_language_rewriter'),
            stones_alignment_filter=MockGateAdapter('stones_alignment_filter'),
            coherence_gate=MockGateAdapter('coherence_gate')
        )
    
    @pytest.fixture
    def mock_pace(self):
        """Mock pace policy"""
        return MockPacePolicy('NOW')
    
    @pytest.fixture
    def mock_consent(self):
        """Mock consent policy"""
        return MockConsentPolicy('YES')
    
    @pytest.fixture
    def mock_diagnostics(self):
        """Mock diagnostics policy"""
        return MockDiagnosticsPolicy()
    
    @pytest.fixture
    def mock_completion(self):
        """Mock completion policy"""
        return MockCompletionPolicy()
    
    @pytest.fixture
    def entry_room(self, mock_gates, mock_pace, mock_consent, mock_diagnostics, mock_completion):
        """Entry Room instance with mocked dependencies"""
        config = EntryRoomConfig(
            gates=mock_gates,
            pace=mock_pace,
            consent=mock_consent,
            diagnostics=mock_diagnostics,
            completion=mock_completion,
            diagnostics_default=True
        )
        return EntryRoom(config)
    
    @pytest.fixture
    def entry_room_with_defaults(self):
        """Entry Room instance with default implementations"""
        return EntryRoom()
    
    @pytest.mark.asyncio
    async def test_faithful_reflection_multiline_payload(self, entry_room, sample_input):
        """Test that multiline payloads are reflected exactly, one idea per line"""
        result = await entry_room.run_entry_room(sample_input)
        
        # Should contain the original ideas, one per line
        assert 'Hello, I have multiple ideas' in result.display_text
        assert 'First idea' in result.display_text
        assert 'Second idea' in result.display_text
        
        # Should be before completion marker
        assert result.display_text.index('Hello, I have multiple ideas') < result.display_text.index('[✓ TEST COMPLETE]')
    
    @pytest.mark.asyncio
    async def test_faithful_reflection_string_payload(self, entry_room):
        """Test that string payloads are handled correctly"""
        input_data = EntryRoomInput(
            session_state_ref='test-session',
            payload='Simple single idea'
        )
        
        result = await entry_room.run_entry_room(input_data)
        assert 'Simple single idea' in result.display_text
    
    @pytest.mark.asyncio
    async def test_faithful_reflection_object_payload(self, entry_room):
        """Test that object payloads with text fields are handled correctly"""
        input_data = EntryRoomInput(
            session_state_ref='test-session',
            payload={'text': 'Object with text field'}
        )
        
        result = await entry_room.run_entry_room(input_data)
        assert 'Object with text field' in result.display_text
    
    @pytest.mark.asyncio
    async def test_faithful_reflection_null_payload(self, entry_room):
        """Test that null/undefined payloads are handled gracefully"""
        input_data = EntryRoomInput(
            session_state_ref='test-session',
            payload=None
        )
        
        result = await entry_room.run_entry_room(input_data)
        assert 'No input provided' in result.display_text
    
    @pytest.mark.asyncio
    async def test_gate_chain_order(self, entry_room, sample_input):
        """Test that gates run in correct order"""
        # Create gates that record their call order
        call_order = []
        
        class OrderedGateAdapter(MockGateAdapter):
            async def run(self, text: str, ctx: Dict[str, Any]) -> GateResult:
                call_order.append(self.name)
                return await super().run(text, ctx)
        
        ordered_gates = GateChainConfig(
            integrity_linter=OrderedGateAdapter('integrity_linter'),
            plain_language_rewriter=OrderedGateAdapter('plain_language_rewriter'),
            stones_alignment_filter=OrderedGateAdapter('stones_alignment_filter'),
            coherence_gate=OrderedGateAdapter('coherence_gate')
        )
        
        config = EntryRoomConfig(gates=ordered_gates)
        test_room = EntryRoom(config)
        
        await test_room.run_entry_room(sample_input)
        
        assert call_order == [
            'integrity_linter',
            'plain_language_rewriter',
            'stones_alignment_filter',
            'coherence_gate'
        ]
    
    @pytest.mark.asyncio
    async def test_gate_chain_halt_on_failure(self, entry_room, sample_input, mock_gates):
        """Test that gate chain halts on first failure"""
        # Make the second gate fail
        mock_gates.plain_language_rewriter = MockGateAdapter('plain_language_rewriter', False)
        
        config = EntryRoomConfig(gates=mock_gates)
        test_room = EntryRoom(config)
        
        result = await test_room.run_entry_room(sample_input)
        
        assert 'Gate plain_language_rewriter declined' in result.display_text
        assert result.next_action == 'hold'
    
    @pytest.mark.asyncio
    async def test_gate_chain_include_notes(self, entry_room, sample_input, mock_gates):
        """Test that gate failures include gate name and notes"""
        failing_gate = MockGateAdapter('test_gate', False, '', ['Custom error note'])
        mock_gates.integrity_linter = failing_gate
        
        config = EntryRoomConfig(gates=mock_gates)
        test_room = EntryRoom(config)
        
        result = await test_room.run_entry_room(sample_input)
        
        assert 'Gate integrity_linter declined' in result.display_text
        assert 'Custom error note' in result.display_text
    
    @pytest.mark.asyncio
    async def test_pace_setting_hold(self, entry_room, sample_input, mock_pace):
        """Test that HOLD pace sets next_action to 'hold'"""
        mock_pace.return_pace = 'HOLD'
        
        config = EntryRoomConfig(pace=mock_pace)
        test_room = EntryRoom(config)
        
        result = await test_room.run_entry_room(sample_input)
        assert result.next_action == 'hold'
    
    @pytest.mark.asyncio
    async def test_pace_setting_later(self, entry_room_with_defaults, sample_input, mock_pace, mock_consent):
        """Test that LATER pace sets next_action to 'later'"""
        mock_pace.return_pace = 'LATER'
        mock_consent.return_consent = 'YES'
        
        config = EntryRoomConfig(pace=mock_pace, consent=mock_consent)
        test_room = EntryRoom(config)
        
        result = await test_room.run_entry_room(sample_input)
        assert result.next_action == 'later'
    
    @pytest.mark.asyncio
    async def test_pace_setting_now(self, entry_room_with_defaults, sample_input, mock_pace, mock_consent):
        """Test that NOW pace sets next_action to 'continue'"""
        mock_pace.return_pace = 'NOW'
        mock_consent.return_consent = 'YES'
        
        config = EntryRoomConfig(pace=mock_pace, consent=mock_consent)
        test_room = EntryRoom(config)
        
        result = await test_room.run_entry_room(sample_input)
        assert result.next_action == 'continue'
    
    @pytest.mark.asyncio
    async def test_pace_setting_soft_hold(self, entry_room, sample_input, mock_pace):
        """Test that SOFT_HOLD pace sets next_action to 'hold'"""
        mock_pace.return_pace = 'SOFT_HOLD'
        
        config = EntryRoomConfig(pace=mock_pace)
        test_room = EntryRoom(config)
        
        result = await test_room.run_entry_room(sample_input)
        assert result.next_action == 'hold'
    
    @pytest.mark.asyncio
    async def test_consent_anchor_short_circuit(self, entry_room, sample_input, mock_consent):
        """Test that consent short-circuits with consent prompt when not YES"""
        mock_consent.return_consent = 'HOLD'
        
        config = EntryRoomConfig(consent=mock_consent)
        test_room = EntryRoom(config)
        
        result = await test_room.run_entry_room(sample_input)
        
        assert 'Before we proceed, I need your explicit consent' in result.display_text
        assert result.next_action == 'hold'
    
    @pytest.mark.asyncio
    async def test_consent_anchor_later_action(self, entry_room, sample_input, mock_consent):
        """Test that LATER consent returns 'later' action"""
        mock_consent.return_consent = 'LATER'
        
        config = EntryRoomConfig(consent=mock_consent)
        test_room = EntryRoom(config)
        
        result = await test_room.run_entry_room(sample_input)
        
        assert 'prefer to continue later' in result.display_text
        assert result.next_action == 'later'
    
    @pytest.mark.asyncio
    async def test_consent_anchor_proceed_on_yes(self, entry_room_with_defaults, sample_input, mock_consent):
        """Test that YES consent allows normal progression"""
        mock_consent.return_consent = 'YES'
        
        config = EntryRoomConfig(consent=mock_consent)
        test_room = EntryRoom(config)
        
        result = await test_room.run_entry_room(sample_input)
        
        assert result.next_action == 'continue'
        assert '[✓ Entry Room Complete]' in result.display_text
    
    @pytest.mark.asyncio
    async def test_diagnostics_enabled(self, entry_room_with_defaults, sample_input, mock_diagnostics, mock_consent):
        """Test that diagnostics are captured when enabled"""
        mock_consent.return_consent = 'YES'
        config = EntryRoomConfig(diagnostics=mock_diagnostics, diagnostics_default=True, consent=mock_consent)
        test_room = EntryRoom(config)
        
        await test_room.run_entry_room(sample_input)
        
        assert len(mock_diagnostics.captured_diagnostics) == 1
        assert mock_diagnostics.captured_diagnostics[0]['input'] == sample_input
    
    @pytest.mark.asyncio
    async def test_diagnostics_disabled(self, entry_room, sample_input, mock_diagnostics):
        """Test that diagnostics are skipped when disabled"""
        config = EntryRoomConfig(diagnostics=mock_diagnostics, diagnostics_default=False)
        test_room = EntryRoom(config)
        
        await test_room.run_entry_room(sample_input)
        
        assert len(mock_diagnostics.captured_diagnostics) == 0
    
    @pytest.mark.asyncio
    async def test_diagnostics_failure_doesnt_break_flow(self, entry_room_with_defaults, sample_input, mock_consent):
        """Test that diagnostics failure doesn't break main flow"""
        mock_consent.return_consent = 'YES'
        failing_diagnostics = type('FailingDiagnostics', (), {
            'capture_diagnostics': lambda *args, **kwargs: (_ for _ in ()).throw(Exception('Diagnostics failed'))
        })()
        
        config = EntryRoomConfig(diagnostics=failing_diagnostics, consent=mock_consent)
        test_room = EntryRoom(config)
        
        result = await test_room.run_entry_room(sample_input)
        
        # Should still complete successfully
        assert '[✓ Entry Room Complete]' in result.display_text
    
    @pytest.mark.asyncio
    async def test_completion_marker_appended(self, entry_room, sample_input):
        """Test that completion marker is always appended"""
        result = await entry_room.run_entry_room(sample_input)
        
        assert result.display_text.endswith('[✓ TEST COMPLETE]')
    
    @pytest.mark.asyncio
    async def test_completion_marker_with_gate_modifications(self, entry_room_with_defaults, sample_input, mock_gates, mock_consent):
        """Test that completion marker is added even when gates modify text"""
        mock_consent.return_consent = 'YES'
        # Make a gate modify the text
        mock_gates.plain_language_rewriter = MockGateAdapter(
            'plain_language_rewriter',
            True,
            'Modified text by gate'
        )
        
        config = EntryRoomConfig(gates=mock_gates, consent=mock_consent)
        test_room = EntryRoom(config)
        
        result = await test_room.run_entry_room(sample_input)
        
        assert 'Modified text by gate' in result.display_text
        assert result.display_text.endswith('[✓ Entry Room Complete]')
    
    @pytest.mark.asyncio
    async def test_contract_io_compliance(self, entry_room, sample_input):
        """Test that output matches contract shape exactly"""
        result = await entry_room.run_entry_room(sample_input)
        
        # Check required properties
        assert hasattr(result, 'display_text')
        assert hasattr(result, 'next_action')
        assert isinstance(result.display_text, str)
        assert result.next_action in ['continue', 'hold', 'later']
        
        # Check no additional properties
        assert len(result.__dict__) == 2
    
    @pytest.mark.asyncio
    async def test_error_handling_malformed_input(self, entry_room):
        """Test that malformed input is handled gracefully"""
        malformed_input = EntryRoomInput(
            session_state_ref='test-session',
            payload=None
        )
        
        result = await entry_room.run_entry_room(malformed_input)
        
        assert 'No input provided' in result.display_text
        assert result.next_action == 'continue'
    
    @pytest.mark.asyncio
    async def test_error_handling_gate_exceptions(self, entry_room, sample_input, mock_gates):
        """Test that gate exceptions are handled gracefully"""
        throwing_gate = type('ThrowingGate', (), {
            'run': lambda *args, **kwargs: (_ for _ in ()).throw(Exception('Gate crashed'))
        })()
        
        mock_gates.integrity_linter = throwing_gate
        
        config = EntryRoomConfig(gates=mock_gates)
        test_room = EntryRoom(config)
        
        result = await test_room.run_entry_room(sample_input)
        
        assert 'Gate integrity_linter error' in result.display_text
        assert result.next_action == 'hold'
    
    @pytest.mark.asyncio
    async def test_error_handling_no_unhandled_exceptions(self, entry_room):
        """Test that no unhandled exceptions are thrown"""
        problematic_input = EntryRoomInput(
            session_state_ref='test-session',
            payload='Normal payload'
        )
        
        # Should not throw
        result = await entry_room.run_entry_room(problematic_input)
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_integration_full_flow_success(self, entry_room, sample_input):
        """Test that full flow completes successfully with valid input"""
        result = await entry_room.run_entry_room(sample_input)
        
        assert 'Hello, I have multiple ideas' in result.display_text
        assert 'First idea' in result.display_text
        assert 'Second idea' in result.display_text
        assert result.display_text.endswith('[✓ TEST COMPLETE]')
        assert result.next_action == 'continue'
    
    @pytest.mark.asyncio
    async def test_integration_complex_multi_idea_payloads(self, entry_room):
        """Test handling of complex multi-idea payloads"""
        complex_input = EntryRoomInput(
            session_state_ref='complex-session',
            payload="""I have several concerns:
1. First concern about timing
2. Second concern about quality
3. Third concern about resources"""
        )
        
        result = await entry_room.run_entry_room(complex_input)
        
        assert 'I have several concerns:' in result.display_text
        assert '1. First concern about timing' in result.display_text
        assert '2. Second concern about quality' in result.display_text
        assert '3. Third concern about resources' in result.display_text


class TestRunEntryRoomFunction:
    """Test suite for standalone run_entry_room function"""
    
    @pytest.mark.asyncio
    async def test_standalone_function_callable(self):
        """Test that run_entry_room function is callable as standalone function"""
        input_data = EntryRoomInput(
            session_state_ref='standalone-test',
            payload='Test payload'
        )
        
        result = await run_entry_room(input_data)
        
        assert isinstance(result, dict)
        assert 'display_text' in result
        assert 'next_action' in result
    
    @pytest.mark.asyncio
    async def test_standalone_function_accepts_config(self):
        """Test that run_entry_room function accepts optional configuration"""
        input_data = EntryRoomInput(
            session_state_ref='config-test',
            payload='Test payload'
        )
        
        custom_completion = type('CustomCompletion', (), {
            'append_completion_marker': lambda self, text: text + '\n[CUSTOM MARKER]'
        })()
        
        class CustomConsent:
            async def enforce_consent(self, ctx):
                return 'YES'
        
        custom_consent = CustomConsent()
        
        config = EntryRoomConfig(
            completion=custom_completion,
            consent=custom_consent
        )
        
        result = await run_entry_room(input_data, config)
        
        assert isinstance(result, dict)
        assert '[CUSTOM MARKER]' in result['display_text']
