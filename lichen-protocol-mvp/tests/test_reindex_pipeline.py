"""
Tests for the Canon Reindex Pipeline.

Tests cover file detection, chunker CLI integration, stats diffing, 
atomic operations, and git hygiene checks.
"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import pytest

from tools.reindex_pipeline import ReindexPipeline, ReindexStats


class TestReindexStats:
    """Test ReindexStats functionality."""
    
    def test_stats_initialization(self):
        """Test that stats initialize with correct defaults."""
        stats = ReindexStats()
        
        assert stats.protocols_count == 0
        assert stats.total_tokens == 0
        assert stats.avg_chunk_size == 0.0
        assert stats.overlap_stats == {}
        assert stats.stones_coverage == set()
        assert stats.fields_coverage == set()
        assert stats.manifest_data == {}
    
    def test_stats_from_manifest_file(self):
        """Test loading stats from a manifest file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_data = {
                "protocols": 5,
                "total_tokens": 1200,
                "avg_chunk_size": 240.0,
                "stones_coverage": ["light-before-form", "speed-of-trust"],
                "fields_coverage": ["title", "content", "stones"]
            }
            json.dump(test_data, f)
            manifest_path = Path(f.name)
        
        try:
            stats = ReindexStats.from_manifest_file(manifest_path)
            
            assert stats.protocols_count == 5
            assert stats.total_tokens == 1200
            assert stats.avg_chunk_size == 240.0
            assert stats.stones_coverage == {"light-before-form", "speed-of-trust"}
            assert stats.fields_coverage == {"title", "content", "stones"}
        finally:
            os.unlink(manifest_path)
    
    def test_stats_from_missing_file(self):
        """Test loading stats from non-existent file."""
        non_existent = Path("/tmp/non_existent_manifest.json")
        stats = ReindexStats.from_manifest_file(non_existent)
        
        assert stats.protocols_count == 0
        assert stats.stones_coverage == set()
    
    def test_stats_to_dict(self):
        """Test converting stats to dictionary."""
        stats = ReindexStats()
        stats.protocols_count = 10
        stats.total_tokens = 2400
        stats.stones_coverage = {"light-before-form", "speed-of-trust"}
        stats.fields_coverage = {"title", "content"}
        
        result = stats.to_dict()
        
        assert result["protocols"] == 10
        assert result["total_tokens"] == 2400
        assert set(result["stones_coverage"]) == {"light-before-form", "speed-of-trust"}
        assert set(result["fields_coverage"]) == {"title", "content"}


class TestReindexPipeline:
    """Test ReindexPipeline functionality."""
    
    def test_pipeline_initialization(self):
        """Test pipeline initializes with correct paths."""
        pipeline = ReindexPipeline()
        
        # Should set up expected paths
        assert pipeline.canon_path.name == "Protocol_Canon"
        assert pipeline.schema_path.name == "protocol_template_schema_v1.json"
        assert pipeline.speed_index_dir.name == "speed"
        assert pipeline.accuracy_index_dir.name == "accuracy"
    
    @patch('tools.reindex_pipeline.CANON_PATH')
    def test_find_changed_files(self, mock_canon_path):
        """Test finding changed files in canon directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_canon_path.return_value = temp_path
            
            # Create test files with different timestamps
            old_file = temp_path / "old.json"
            new_file = temp_path / "new.json"
            
            old_file.write_text('{"title": "old"}')
            time.sleep(0.1)  # Ensure different timestamps
            new_file.write_text('{"title": "new"}')
            
            pipeline = ReindexPipeline()
            pipeline.canon_path = temp_path
            
            # Find all files
            all_files = pipeline.find_changed_files()
            assert len(all_files) == 2
            
            # Find files changed in last 1 minute (should be all)
            recent_files = pipeline.find_changed_files(since_minutes=1)
            assert len(recent_files) == 2
            
            # Find files changed in last 0 minutes (should be none due to cutoff)
            no_files = pipeline.find_changed_files(since_minutes=0)
            assert len(no_files) == 0
    
    @patch('subprocess.run')
    def test_run_chunker_cli_success(self, mock_run):
        """Test successful chunker CLI execution."""
        mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")
        
        pipeline = ReindexPipeline()
        result = pipeline.run_chunker_cli("speed")
        
        assert result is True
        mock_run.assert_called_once()
        
        # Check command arguments
        call_args = mock_run.call_args[0][0]
        assert "python" in call_args
        assert "-m" in call_args
        assert "lichen_chunker.cli" in call_args
        assert "process" in call_args
        assert "--profile" in call_args
        assert "speed" in call_args
    
    @patch('subprocess.run')
    def test_run_chunker_cli_failure(self, mock_run):
        """Test chunker CLI execution failure."""
        mock_run.return_value = MagicMock(
            returncode=1, 
            stdout="", 
            stderr="chunker failed"
        )
        
        pipeline = ReindexPipeline()
        result = pipeline.run_chunker_cli("accuracy")
        
        assert result is False
    
    def test_scan_canon_for_stats(self):
        """Test scanning canon directory for statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test protocol files
            protocol1 = temp_path / "protocol1.json"
            protocol2 = temp_path / "protocol2.json"
            
            protocol1_data = {
                "title": "Test Protocol 1",
                "content": "This is a test protocol with some content here",
                "stones": ["light-before-form", "speed-of-trust"],
                "extra_field": "value"
            }
            
            protocol2_data = {
                "title": "Test Protocol 2", 
                "Content": "Another test protocol with different content",  # Capital C
                "stones": ["essence-first"],
                "different_field": "value"
            }
            
            protocol1.write_text(json.dumps(protocol1_data))
            protocol2.write_text(json.dumps(protocol2_data))
            
            pipeline = ReindexPipeline()
            pipeline.canon_path = temp_path
            
            stats = pipeline.scan_canon_for_stats()
            
            assert stats.protocols_count == 2
            assert stats.total_tokens > 0  # Should count words and convert to tokens
            assert "light-before-form" in stats.stones_coverage
            assert "speed-of-trust" in stats.stones_coverage
            assert "essence-first" in stats.stones_coverage
            assert "title" in stats.fields_coverage
            assert "content" in stats.fields_coverage
            assert "Content" in stats.fields_coverage
            assert "extra_field" in stats.fields_coverage
            assert "different_field" in stats.fields_coverage
    
    def test_compute_stats_diff(self):
        """Test computing statistics differences."""
        before_stats = ReindexStats()
        before_stats.protocols_count = 5
        before_stats.total_tokens = 1000
        before_stats.stones_coverage = {"light-before-form", "speed-of-trust"}
        before_stats.fields_coverage = {"title", "content"}
        before_stats.avg_chunk_size = 200.0
        
        after_stats = ReindexStats()
        after_stats.protocols_count = 7
        after_stats.total_tokens = 1500
        after_stats.stones_coverage = {"light-before-form", "essence-first", "truth-over-comfort"}
        after_stats.fields_coverage = {"title", "content", "stones"}
        after_stats.avg_chunk_size = 214.0
        
        pipeline = ReindexPipeline()
        diff = pipeline.compute_stats_diff(before_stats, after_stats)
        
        assert diff["protocols_before"] == 5
        assert diff["protocols_after"] == 7
        assert diff["tokens_added"] == 500
        assert diff["tokens_removed"] == 0
        assert "light-before-form" in diff["stones_coverage_before"]
        assert "light-before-form" in diff["stones_coverage_after"]
        assert "essence-first" in diff["stones_coverage_after"]
        assert "essence-first" not in diff["stones_coverage_before"]
        assert diff["avg_chunk_size_before"] == 200.0
        assert diff["avg_chunk_size_after"] == 214.0
    
    @patch('tools.reindex_pipeline.datetime')
    def test_log_reindex_event(self, mock_datetime):
        """Test logging reindex events to JSONL."""
        mock_now = MagicMock()
        mock_now.strftime.return_value = "2025-09-12"
        mock_now.isoformat.return_value = "2025-09-12T04:32:01+00:00"
        mock_datetime.now.return_value = mock_now
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            
            pipeline = ReindexPipeline()
            pipeline.reindex_log_dir = log_dir
            
            changed_files = [Path("protocol1.json"), Path("protocol2.json")]
            stats_diff = {
                "protocols_before": 5,
                "protocols_after": 6,
                "tokens_added": 200
            }
            
            pipeline.log_reindex_event(changed_files, stats_diff)
            
            # Check log file was created
            log_file = log_dir / "2025-09-12.jsonl"
            assert log_file.exists()
            
            # Check log content
            with open(log_file) as f:
                log_entry = json.loads(f.read().strip())
            
            assert log_entry["event"] == "reindex"
            assert log_entry["changed_files"] == ["protocol1.json", "protocol2.json"]
            assert log_entry["stats_diff"]["protocols_before"] == 5
            assert log_entry["stats_diff"]["protocols_after"] == 6
            assert "ts" in log_entry
    
    @patch.object(ReindexPipeline, 'move_indexes_atomically')
    @patch.object(ReindexPipeline, 'run_chunker_cli')
    @patch.object(ReindexPipeline, 'collect_stats_from_manifest')
    @patch.object(ReindexPipeline, 'scan_canon_for_stats')
    @patch.object(ReindexPipeline, 'log_reindex_event')
    def test_reindex_once_success(self, mock_log, mock_scan, mock_collect, mock_cli, mock_move):
        """Test successful one-shot reindex operation."""
        # Mock successful operations
        mock_cli.return_value = True
        mock_move.return_value = True
        
        # Mock stats
        before_stats = ReindexStats()
        before_stats.protocols_count = 5
        
        after_stats = ReindexStats()
        after_stats.protocols_count = 6
        
        mock_collect.return_value = before_stats
        mock_scan.return_value = after_stats
        
        pipeline = ReindexPipeline()
        changed_files = [Path("test.json")]
        
        result = pipeline.reindex_once(changed_files)
        
        assert result is True
        
        # Verify all steps were called
        assert mock_cli.call_count == 2  # Called for both speed and accuracy
        mock_move.assert_called_once()
        mock_log.assert_called_once()
    
    @patch.object(ReindexPipeline, 'run_chunker_cli')
    def test_reindex_once_chunker_failure(self, mock_cli):
        """Test reindex failure when chunker CLI fails."""
        # Mock chunker failure
        mock_cli.side_effect = [True, False]  # speed succeeds, accuracy fails
        
        pipeline = ReindexPipeline()
        result = pipeline.reindex_once([])
        
        assert result is False


class TestGitHygiene:
    """Test git hygiene and pre-commit hooks."""
    
    def test_block_vector_files_script_exists(self):
        """Test that the block vector files script exists and is executable."""
        script_path = Path("tools/block_vector_files.py")
        
        assert script_path.exists()
        assert os.access(script_path, os.X_OK)  # Check if executable
    
    def test_gitignore_contains_vector_paths(self):
        """Test that .gitignore contains required vector paths."""
        gitignore_path = Path(".gitignore")
        
        with open(gitignore_path) as f:
            content = f.read()
        
        assert "lichen-chunker/index/**" in content
        assert ".vector/" in content
        assert "logs/rag/" in content
    
    def test_precommit_config_contains_vector_hook(self):
        """Test that pre-commit config contains vector file blocking hook."""
        precommit_path = Path(".pre-commit-config.yaml")
        
        with open(precommit_path) as f:
            content = f.read()
        
        assert "block-vector-files" in content
        assert "tools/block_vector_files.py" in content
    
    @patch('subprocess.run')
    def test_block_vector_files_detects_violations(self, mock_run):
        """Test that vector file blocking script detects violations."""
        from tools.block_vector_files import main
        
        # Test with vector file path
        import sys
        original_argv = sys.argv
        
        try:
            sys.argv = ["block_vector_files.py", ".vector/test.faiss"]
            
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1
            
        finally:
            sys.argv = original_argv
    
    @patch('subprocess.run')  
    def test_block_vector_files_allows_normal_files(self, mock_run):
        """Test that vector file blocking script allows normal files."""
        from tools.block_vector_files import main
        
        import sys
        original_argv = sys.argv
        
        try:
            sys.argv = ["block_vector_files.py", "src/main.py", "README.md"]
            
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
            
        finally:
            sys.argv = original_argv


class TestIntegration:
    """Integration tests for complete reindex pipeline."""
    
    @patch('subprocess.run')
    def test_end_to_end_reindex_simulation(self, mock_run):
        """Test simulated end-to-end reindex operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock canon files
            protocol_file = temp_path / "test_protocol.json"
            protocol_data = {
                "title": "Integration Test Protocol",
                "content": "This is a test protocol for integration testing",
                "stones": ["light-before-form", "speed-of-trust"]
            }
            protocol_file.write_text(json.dumps(protocol_data))
            
            # Mock successful chunker CLI runs
            mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")
            
            pipeline = ReindexPipeline()
            pipeline.canon_path = temp_path
            
            # Mock the index movement (since we don't have real chunker output)
            with patch.object(pipeline, 'move_indexes_atomically', return_value=True):
                result = pipeline.reindex_once()
            
            assert result is True
            
            # Verify chunker was called for both profiles
            assert mock_run.call_count >= 2
            
            # Check that log was created
            log_files = list(pipeline.reindex_log_dir.glob("*.jsonl"))
            assert len(log_files) >= 1
    
    def test_stones_coverage_validation(self):
        """Test that stones coverage validation works correctly."""
        from tools.reindex_pipeline import STONES_LIST
        
        # Should have all 10 stones defined
        assert len(STONES_LIST) == 10
        assert "light-before-form" in STONES_LIST
        assert "speed-of-trust" in STONES_LIST
        assert "field-before-stones" in STONES_LIST
        assert "essence-first" in STONES_LIST
        assert "truth-over-comfort" in STONES_LIST
        assert "energy-follows-attention" in STONES_LIST
        assert "dynamics-over-content" in STONES_LIST
        assert "evolutionary-edge" in STONES_LIST
        assert "aligned-action" in STONES_LIST
        assert "presence-over-perfection" in STONES_LIST