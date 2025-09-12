"""
Tests for performance budget instrumentation and validation.

These are sanity checks to ensure budget logic is wired correctly.
Not full performance benchmarks - just validates the instrumentation.
"""

import time
import asyncio
import pytest
from unittest.mock import patch, MagicMock
from ..orchestrator import _is_warmup_query, _get_timing_ms, _run_rag_retrieval
from ..types import ExecutionContext


class TestPerformanceBudgets:
    """Test performance budget instrumentation."""
    
    def test_warmup_counter_tracks_correctly(self):
        """Test that warmup counter tracks first 3 queries correctly."""
        # Reset global counter for test isolation
        import hallway.orchestrator as orch
        orch._warmup_counter = 0
        
        # First 3 should be warmup
        assert _is_warmup_query() == True  # 1st query
        assert _is_warmup_query() == True  # 2nd query  
        assert _is_warmup_query() == True  # 3rd query
        
        # 4th and beyond should not be warmup
        assert _is_warmup_query() == False  # 4th query
        assert _is_warmup_query() == False  # 5th query
    
    def test_high_precision_timing(self):
        """Test that timing has microsecond precision."""
        start = time.perf_counter()
        # Small delay to test precision
        time.sleep(0.001)  # 1ms
        elapsed_ms = _get_timing_ms(start)
        
        # Should be around 1ms with sub-millisecond precision
        assert 0.5 < elapsed_ms < 5.0  # Allow some variance
        assert isinstance(elapsed_ms, float)
        
        # Check precision - should have decimals
        assert elapsed_ms != int(elapsed_ms)
    
    def test_budget_targets_exist(self):
        """Test that performance budget targets are defined."""
        from tools.tail_rag_logs import RAGLogTailer
        
        # Mock args
        args = MagicMock()
        args.p95_window = 200
        args.budget_check = False
        
        tailer = RAGLogTailer(args)
        
        # Verify budget targets are defined
        assert "fast" in tailer.budget_targets
        assert "accurate" in tailer.budget_targets
        assert tailer.budget_targets["fast"] == 150.0
        assert tailer.budget_targets["accurate"] == 500.0
        
        # Verify lane trackers are set up
        assert "fast" in tailer.p95_by_lane
        assert "accurate" in tailer.p95_by_lane
    
    def test_budget_filtering_excludes_warmup(self):
        """Test that budget check filtering excludes warmup events."""
        from tools.tail_rag_logs import RAGLogTailer
        
        args = MagicMock()
        args.p95_window = 200
        args.budget_check = True
        args.since = None
        
        tailer = RAGLogTailer(args)
        
        # Warmup event should be filtered out
        warmup_event = {
            "lane": "fast",
            "stages": {"total_ms": 100.0},
            "flags": {"warmup": True}
        }
        assert not tailer.matches_budget_filters(warmup_event)
        
        # Non-warmup event should pass
        normal_event = {
            "lane": "fast", 
            "stages": {"total_ms": 100.0},
            "flags": {"warmup": False}
        }
        assert tailer.matches_budget_filters(normal_event)
        
        # Event without timing should be filtered out
        no_timing_event = {
            "lane": "fast",
            "stages": {},
            "flags": {"warmup": False}
        }
        assert not tailer.matches_budget_filters(no_timing_event)
    
    @pytest.mark.asyncio
    @patch('hallway.adapters.rag_adapter.get_rag_adapter')
    async def test_timing_instrumentation_in_orchestrator(self, mock_get_adapter):
        """Test that orchestrator properly instruments timing with warmup flags."""
        # Mock the RAG adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_get_adapter.return_value = mock_adapter
        
        # Mock retrieval with simulated delay
        def mock_retrieve(query, lane):
            time.sleep(0.001)  # 1ms delay
            return [{"doc": "test_doc", "text": "test context", "score": 0.8}]
        mock_adapter.retrieve.side_effect = mock_retrieve
        
        # Mock generation with simulated delay
        def mock_generate(query, context_texts, lane):
            time.sleep(0.001)  # 1ms delay
            return {
                "answer": "test answer", 
                "citations": [{"source_id": "test_doc", "span": [0, 10]}],
                "hallucinations": 0
            }
        mock_adapter.generate.side_effect = mock_generate
        mock_adapter.stones_align.return_value = 0.8
        mock_adapter.is_sufficient_support.return_value = True
        
        # Create execution context
        ctx = ExecutionContext(
            run_id="test-run",
            correlation_id="test-correlation", 
            rooms_to_run=["ai_room"],
            budgets={},
            policy={},
            ports=MagicMock(),
            state={
                "payloads": {
                    "ai_room": {
                        "brief": {"task": "test query", "stones": []}
                    }
                }
            }
        )
        
        # Reset warmup counter
        import hallway.orchestrator as orch
        orch._warmup_counter = 0
        
        with patch('hallway.orchestrator.log_rag_turn') as mock_log:
            result = await _run_rag_retrieval(ctx)
            
            # Verify logging was called
            mock_log.assert_called_once()
            
            # Check timing precision and warmup flag
            call_args = mock_log.call_args
            stages = call_args.kwargs['stages']
            flags = call_args.kwargs['flags']
            
            # Verify high precision timing (should have decimals)
            assert isinstance(stages['retrieve_ms'], float)
            assert isinstance(stages['synth_ms'], float)  
            assert isinstance(stages['total_ms'], float)
            
            # Verify timing values are reasonable (> 0, < 100ms for test)
            assert 0 < stages['retrieve_ms'] < 100
            assert 0 < stages['synth_ms'] < 100
            assert 0 < stages['total_ms'] < 100
            
            # Verify warmup flag is present and correct
            assert 'warmup' in flags
            assert flags['warmup'] == True  # First query should be warmup
    
    def test_performance_config_values(self):
        """Test that performance configuration values are sensible."""
        from tools.tail_rag_logs import RAGLogTailer
        
        args = MagicMock()
        args.p95_window = 200
        args.budget_check = False
        
        tailer = RAGLogTailer(args)
        
        # Fast lane should be more aggressive than accurate
        assert tailer.budget_targets["fast"] < tailer.budget_targets["accurate"]
        
        # Targets should be reasonable (not too low or too high)
        assert 50 <= tailer.budget_targets["fast"] <= 1000  # 50ms - 1s
        assert 100 <= tailer.budget_targets["accurate"] <= 5000  # 100ms - 5s
        
        # Specific target validation
        assert tailer.budget_targets["fast"] == 150.0
        assert tailer.budget_targets["accurate"] == 500.0
    
    def test_budget_check_report_formatting(self):
        """Test that budget check reports format correctly.""" 
        from tools.tail_rag_logs import RAGLogTailer, RollingPercentiles
        
        args = MagicMock()
        args.p95_window = 200
        args.budget_check = True
        
        tailer = RAGLogTailer(args)
        
        # Add some mock data
        tailer.p95_by_lane["fast"].add(100.0)  # Under budget
        tailer.p95_by_lane["accurate"].add(600.0)  # Over budget
        
        # Test that percentiles are calculated
        fast_p95 = tailer.p95_by_lane["fast"].p95()
        accurate_p95 = tailer.p95_by_lane["accurate"].p95()
        
        assert fast_p95 == 100.0
        assert accurate_p95 == 600.0
        
        # Test budget evaluation logic
        fast_over_budget = fast_p95 > tailer.budget_targets["fast"]
        accurate_over_budget = accurate_p95 > tailer.budget_targets["accurate"] 
        
        assert not fast_over_budget  # 100ms < 150ms target
        assert accurate_over_budget  # 600ms > 500ms target


class TestPerformanceConstants:
    """Test that performance constants are properly defined."""
    
    def test_warmup_threshold_constant(self):
        """Test that warmup threshold is properly defined."""
        import hallway.orchestrator as orch
        
        # Should be defined as module-level constant
        assert hasattr(orch, '_warmup_threshold')
        assert isinstance(orch._warmup_threshold, int)
        assert orch._warmup_threshold == 3  # Should be exactly 3
    
    def test_timing_precision_constants(self):
        """Test that timing uses appropriate precision."""
        # Test that we're using perf_counter for precision
        start = time.perf_counter()
        elapsed = _get_timing_ms(start)
        
        # Should be a float with reasonable precision
        assert isinstance(elapsed, float)
        assert elapsed >= 0
    
    def test_budget_targets_as_constants(self):
        """Verify budget targets match specification."""
        from tools.tail_rag_logs import RAGLogTailer
        
        args = MagicMock()
        args.p95_window = 200
        args.budget_check = False
        
        tailer = RAGLogTailer(args) 
        
        # These should match the exact specification
        assert tailer.budget_targets["fast"] == 150.0  # p95 < 150ms
        assert tailer.budget_targets["accurate"] == 500.0  # p95 < 500ms