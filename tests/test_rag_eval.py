"""
Test suite for RAG evaluation harness.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def test_rag_eval_harness():
    """Test the complete RAG evaluation harness end-to-end."""
    
    # Create a minimal test evalset
    test_evalset = [
        {
            "query_id": "q-001",
            "query": "What is the leadership approach for sustainable growth?",
            "gold_doc_ids": ["the_leadership_im_actually_carrying"],
            "expected_stones": ["Clarity Over Cleverness", "Integrity Is the Growth Strategy"],
            "top_k_for_generation": 8
        }
    ]
    
    # Write test evalset to file
    os.makedirs("eval", exist_ok=True)
    with open("eval/evalset.json", "w") as f:
        json.dump(test_evalset, f, indent=2)
    
    # Run the evaluation harness
    result = subprocess.run([
        sys.executable, "-m", "eval.run_eval",
        "--evalset", "eval/evalset.json",
        "--outdir", "eval/out"
    ], capture_output=True, text=True)
    
    # Assert exit code is 0
    assert result.returncode == 0, f"CLI failed with return code {result.returncode}. Stderr: {result.stderr}"
    
    # Assert output files exist
    expected_files = [
        "eval/out/records_fast.jsonl",
        "eval/out/records_accurate.jsonl", 
        "eval/out/summary_fast.json",
        "eval/out/summary_accurate.json"
    ]
    
    for file_path in expected_files:
        assert os.path.exists(file_path), f"Expected file {file_path} not found"
    
    # Verify record files contain expected structure
    for lane in ["fast", "accurate"]:
        records_path = f"eval/out/records_{lane}.jsonl"
        with open(records_path, "r") as f:
            lines = f.readlines()
            assert len(lines) == 1, f"Expected 1 record in {records_path}, found {len(lines)}"
            
            record = json.loads(lines[0])
            required_fields = [
                "query_id", "query", "lane", "ranked_doc_ids", "gold_doc_ids",
                "expected_stones", "diversity_top8", "coverage", "latency_ms",
                "answer", "hallucinations", "grounding_score", "stones_alignment"
            ]
            
            for field in required_fields:
                assert field in record, f"Missing field {field} in record"
            
            assert record["lane"] == lane
            assert record["query_id"] == "q-001"
            assert len(record["ranked_doc_ids"]) >= 20, "Expected at least 20 ranked documents"
    
    # Verify summary files contain expected structure
    for lane in ["fast", "accurate"]:
        summary_path = f"eval/out/summary_{lane}.json"
        with open(summary_path, "r") as f:
            summary = json.load(f)
            
            required_fields = [
                "lane", "num_queries", "precision_at_5", "recall_at_20", "mrr_at_10",
                "ndcg_at_10", "coverage", "latency_ms_p95", "diversity_avg_top8",
                "stones_alignment", "grounding_1to5", "hallucination_rate"
            ]
            
            for field in required_fields:
                assert field in summary, f"Missing field {field} in summary"
            
            assert summary["lane"] == lane
            assert summary["num_queries"] == 1
            
            # Verify metrics are in reasonable ranges
            assert 0.0 <= summary["precision_at_5"] <= 1.0
            assert 0.0 <= summary["recall_at_20"] <= 1.0
            assert 0.0 <= summary["mrr_at_10"] <= 1.0
            assert 0.0 <= summary["ndcg_at_10"] <= 1.0
            assert 0.0 <= summary["coverage"] <= 1.0
            assert summary["latency_ms_p95"] > 0
            assert summary["diversity_avg_top8"] > 0
            assert 0.0 <= summary["stones_alignment"] <= 1.0
            assert 1.0 <= summary["grounding_1to5"] <= 5.0
            assert summary["hallucination_rate"] >= 0.0


def test_evalset_with_empty_gold():
    """Test evaluation with empty gold document IDs to verify coverage behavior."""
    
    # Create evalset with empty gold_doc_ids
    test_evalset = [
        {
            "query_id": "q-002", 
            "query": "What are the key principles of effective leadership?",
            "gold_doc_ids": [],  # Empty gold set
            "expected_stones": ["Presence Is Productivity"],
            "top_k_for_generation": 8
        }
    ]
    
    # Write test evalset
    with open("eval/evalset.json", "w") as f:
        json.dump(test_evalset, f, indent=2)
    
    # Run evaluation
    result = subprocess.run([
        sys.executable, "-m", "eval.run_eval",
        "--evalset", "eval/evalset.json", 
        "--outdir", "eval/out"
    ], capture_output=True, text=True)
    
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    
    # Check that coverage is handled correctly for empty gold sets
    for lane in ["fast", "accurate"]:
        summary_path = f"eval/out/summary_{lane}.json"
        with open(summary_path, "r") as f:
            summary = json.load(f)
            # Coverage should be 1.0 when gold_doc_ids is empty
            assert summary["coverage"] == 1.0, "Coverage should be 1.0 for empty gold sets"


def test_metrics_calculations():
    """Test individual metric calculations."""
    from eval.metrics import (
        precision_at_k, recall_at_k, rr_at_k, ndcg_at_k,
        diversity_unique_docs_topk, simple_grounding_score, stones_alignment_score
    )
    
    # Test precision_at_k
    ranked_docs = ["doc1", "doc2", "doc3", "doc4", "doc5"]
    gold_docs = {"doc2", "doc4"}
    assert precision_at_k(ranked_docs, gold_docs, 3) == 1/3  # 1 relevant out of 3 (doc2 is at index 1)
    
    # Test recall_at_k  
    assert recall_at_k(ranked_docs, gold_docs, 5) == 1.0  # All 2 relevant found in top 5
    assert recall_at_k(ranked_docs, gold_docs, 2) == 1/2  # Only 1 of 2 relevant in top 2
    
    # Test rr_at_k
    assert rr_at_k(ranked_docs, gold_docs, 5) == 0.5  # First relevant at rank 2
    assert rr_at_k(ranked_docs, gold_docs, 1) == 0.0  # No relevant in top 1
    
    # Test ndcg_at_k
    ndcg = ndcg_at_k(ranked_docs, gold_docs, 5)
    assert 0.0 <= ndcg <= 1.0
    
    # Test diversity
    ranked_pairs = [
        {"doc": "doc1", "text": "text1"},
        {"doc": "doc2", "text": "text2"}, 
        {"doc": "doc1", "text": "text3"},  # Duplicate doc
        {"doc": "doc3", "text": "text4"}
    ]
    assert diversity_unique_docs_topk(ranked_pairs, 4) == 3  # 3 unique docs
    
    # Test grounding score
    answer = "This is a test answer with some context"
    contexts = ["This is context text with some", "additional context information"]
    score = simple_grounding_score(answer, contexts)
    assert 1.0 <= score <= 5.0
    
    # Test stones alignment
    expected_stones = ["Clarity Over Cleverness", "Integrity Is the Growth Strategy"]
    answer_with_stones = "The approach emphasizes clarity over cleverness and integrity as growth strategy"
    alignment = stones_alignment_score(expected_stones, answer_with_stones)
    assert alignment > 0.0  # Should find some matches


if __name__ == "__main__":
    test_rag_eval_harness()
    test_evalset_with_empty_gold()
    test_metrics_calculations()
    print("All tests passed!")
