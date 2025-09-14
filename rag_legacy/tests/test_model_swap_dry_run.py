"""
Unit tests for the model swap dry run tool.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the parent directory to the path to import the tool
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from model_swap_dry_run import ModelSwapDryRun


class TestModelSwapDryRun:
    """Test cases for ModelSwapDryRun class."""
    
    def test_initialization(self):
        """Test ModelSwapDryRun initialization."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            dry_run = ModelSwapDryRun("fast", "sentence-transformers/all-MiniLM-L12-v2", None)
            
            assert dry_run.lane == "fast"
            assert dry_run.new_embed == "sentence-transformers/all-MiniLM-L12-v2"
            assert dry_run.new_reranker is None
            assert dry_run.current_embed == "sentence-transformers/all-MiniLM-L6-v2"
            assert dry_run.current_reranker is None
    
    def test_load_queries(self):
        """Test loading queries from JSONL file."""
        queries_data = [
            {"query": "What is machine learning?", "expected_docs": ["doc1", "doc2"]},
            {"query": "How does neural networks work?", "expected_docs": ["doc3", "doc4"]}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for query in queries_data:
                f.write(f"{query}\n")
            temp_file = f.name
        
        try:
            with patch('builtins.open', side_effect=FileNotFoundError):
                dry_run = ModelSwapDryRun("fast")
                queries = dry_run.load_queries(temp_file)
                
                assert len(queries) == 2
                assert queries[0]["query"] == "What is machine learning?"
                assert queries[1]["query"] == "How does neural networks work?"
        finally:
            os.unlink(temp_file)
    
    def test_calculate_overlap(self):
        """Test overlap calculation."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            dry_run = ModelSwapDryRun("fast")
            
            # Test perfect overlap
            overlap = dry_run._calculate_overlap(["doc1", "doc2"], ["doc1", "doc2"])
            assert overlap == 1.0
            
            # Test partial overlap
            overlap = dry_run._calculate_overlap(["doc1", "doc2"], ["doc1", "doc3"])
            assert overlap == 0.5
            
            # Test no overlap
            overlap = dry_run._calculate_overlap(["doc1", "doc2"], ["doc3", "doc4"])
            assert overlap == 0.0
            
            # Test empty lists
            overlap = dry_run._calculate_overlap([], ["doc1"])
            assert overlap == 0.0
    
    def test_calculate_rank_correlation(self):
        """Test rank correlation calculation."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            dry_run = ModelSwapDryRun("fast")
            
            # Test perfect correlation
            results_a = [{"doc": "doc1", "score": 0.9}, {"doc": "doc2", "score": 0.8}]
            results_b = [{"doc": "doc1", "score": 0.9}, {"doc": "doc2", "score": 0.8}]
            correlation = dry_run._calculate_rank_correlation(results_a, results_b)
            assert correlation == 1.0
            
            # Test reverse correlation
            results_a = [{"doc": "doc1", "score": 0.9}, {"doc": "doc2", "score": 0.8}]
            results_b = [{"doc": "doc2", "score": 0.9}, {"doc": "doc1", "score": 0.8}]
            correlation = dry_run._calculate_rank_correlation(results_a, results_b)
            assert correlation < 1.0
            
            # Test no common documents
            results_a = [{"doc": "doc1", "score": 0.9}]
            results_b = [{"doc": "doc2", "score": 0.9}]
            correlation = dry_run._calculate_rank_correlation(results_a, results_b)
            assert correlation == 0.0
    
    def test_run_query_comparison(self):
        """Test single query comparison."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            dry_run = ModelSwapDryRun("fast", "sentence-transformers/all-MiniLM-L12-v2")
            
            # Mock the RAG adapter
            mock_adapter = MagicMock()
            mock_adapter.retrieve.return_value = [
                {"doc": "doc1", "chunk": 1, "rank": 1, "score": 0.9, "text": "text1"},
                {"doc": "doc2", "chunk": 1, "rank": 2, "score": 0.8, "text": "text2"}
            ]
            dry_run.rag_adapter = mock_adapter
            
            # Mock the proposed models run
            with patch.object(dry_run, '_run_with_proposed_models') as mock_proposed:
                mock_proposed.return_value = {
                    "results": [
                        {"doc": "doc1", "chunk": 1, "rank": 1, "score": 0.95, "text": "text1"},
                        {"doc": "doc3", "chunk": 1, "rank": 2, "score": 0.85, "text": "text3"}
                    ],
                    "latency_ms": 150.0
                }
                
                comparison = dry_run.run_query_comparison("test query", 2)
                
                assert comparison["query"] == "test query"
                assert len(comparison["current"]["results"]) == 2
                assert len(comparison["proposed"]["results"]) == 2
                assert comparison["proposed"]["latency_ms"] == 150.0
                assert "overlap_at_k" in comparison["metrics"]
                assert "rank_correlation" in comparison["metrics"]
                assert "latency_delta_ms" in comparison["metrics"]
    
    def test_run_comparison(self):
        """Test running comparison across multiple queries."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            dry_run = ModelSwapDryRun("fast", "sentence-transformers/all-MiniLM-L12-v2")
            
            # Mock the query comparison
            with patch.object(dry_run, 'run_query_comparison') as mock_comparison:
                mock_comparison.side_effect = [
                    {
                        "query": "query1",
                        "current": {"latency_ms": 100.0},
                        "proposed": {"latency_ms": 120.0},
                        "metrics": {"overlap_at_k": 0.8, "rank_correlation": 0.9, "latency_delta_ms": 20.0}
                    },
                    {
                        "query": "query2",
                        "current": {"latency_ms": 110.0},
                        "proposed": {"latency_ms": 130.0},
                        "metrics": {"overlap_at_k": 0.7, "rank_correlation": 0.8, "latency_delta_ms": 20.0}
                    }
                ]
                
                queries = [
                    {"query": "query1"},
                    {"query": "query2"}
                ]
                
                results = dry_run.run_comparison(queries, 5)
                
                assert results["metadata"]["lane"] == "fast"
                assert results["metadata"]["k"] == 5
                assert results["aggregates"]["num_queries"] == 2
                assert results["aggregates"]["avg_latency_delta_ms"] == 20.0
                assert results["aggregates"]["avg_overlap_at_k"] == 0.75
                assert results["aggregates"]["avg_rank_correlation"] == 0.85
                assert len(results["query_results"]) == 2
    
    def test_generate_report(self):
        """Test report generation."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            dry_run = ModelSwapDryRun("fast", "sentence-transformers/all-MiniLM-L12-v2")
            
            # Mock results
            results = {
                "metadata": {
                    "lane": "fast",
                    "current_models": {"embed_model": "sentence-transformers/all-MiniLM-L6-v2", "reranker_model": None},
                    "proposed_models": {"embed_model": "sentence-transformers/all-MiniLM-L12-v2", "reranker_model": None},
                    "k": 5,
                    "timestamp": "2023-01-01T00:00:00Z"
                },
                "aggregates": {
                    "num_queries": 2,
                    "avg_current_latency_ms": 100.0,
                    "avg_proposed_latency_ms": 120.0,
                    "avg_latency_delta_ms": 20.0,
                    "avg_overlap_at_k": 0.8,
                    "avg_rank_correlation": 0.9
                },
                "query_results": []
            }
            
            with tempfile.TemporaryDirectory() as temp_dir:
                dry_run.generate_report(results, temp_dir)
                
                # Check that files were created
                assert Path(temp_dir, "report.json").exists()
                assert Path(temp_dir, "report.md").exists()
                assert Path(temp_dir, "query_results.csv").exists()
                
                # Check JSON report content
                with open(Path(temp_dir, "report.json"), 'r') as f:
                    json_content = f.read()
                    assert "fast" in json_content
                    assert "sentence-transformers/all-MiniLM-L12-v2" in json_content
                
                # Check Markdown report content
                with open(Path(temp_dir, "report.md"), 'r') as f:
                    md_content = f.read()
                    assert "# Model Swap Dry Run Report" in md_content
                    assert "Lane: fast" in md_content
                    assert "Avg Latency" in md_content


class TestDryRunToolIntegration:
    """Integration tests for the dry run tool."""
    
    def test_environment_variable_override_simulation(self):
        """Test that environment variable overrides work in the dry run tool."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            dry_run = ModelSwapDryRun("fast", "sentence-transformers/all-MiniLM-L12-v2")
            
            # Mock the proposed models run
            with patch.object(dry_run, '_run_with_proposed_models') as mock_proposed:
                mock_proposed.return_value = {
                    "results": [{"doc": "doc1", "chunk": 1, "rank": 1, "score": 0.9, "text": "text1"}],
                    "latency_ms": 150.0
                }
                
                # Mock the RAG adapter
                mock_adapter = MagicMock()
                mock_adapter.retrieve.return_value = [
                    {"doc": "doc1", "chunk": 1, "rank": 1, "score": 0.9, "text": "text1"}
                ]
                dry_run.rag_adapter = mock_adapter
                
                comparison = dry_run.run_query_comparison("test query", 1)
                
                # Verify that the proposed model was used
                assert comparison["proposed"]["embed_model"] == "sentence-transformers/all-MiniLM-L12-v2"
                assert comparison["current"]["embed_model"] == "sentence-transformers/all-MiniLM-L6-v2"
    
    def test_accurate_lane_reranker_comparison(self):
        """Test comparison for accurate lane with reranker models."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            dry_run = ModelSwapDryRun("accurate", None, "cross-encoder/ms-marco-MiniLM-L-6-v2")
            
            # Mock the RAG adapter
            mock_adapter = MagicMock()
            mock_adapter.retrieve.return_value = [
                {"doc": "doc1", "chunk": 1, "rank": 1, "score": 0.9, "text": "text1"}
            ]
            dry_run.rag_adapter = mock_adapter
            
            # Mock the proposed models run
            with patch.object(dry_run, '_run_with_proposed_models') as mock_proposed:
                mock_proposed.return_value = {
                    "results": [{"doc": "doc1", "chunk": 1, "rank": 1, "score": 0.95, "text": "text1"}],
                    "latency_ms": 200.0
                }
                
                comparison = dry_run.run_query_comparison("test query", 1)
                
                # Verify that the proposed reranker was used
                assert comparison["proposed"]["reranker_model"] == "cross-encoder/ms-marco-MiniLM-L-6-v2"
                assert comparison["current"]["reranker_model"] == "cross-encoder/ms-marco-electra-base"


if __name__ == "__main__":
    pytest.main([__file__])
