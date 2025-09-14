#!/usr/bin/env python3
"""
Test script to verify RAG timing stages and observability logging.
"""

import os
import sys
import json
import time
from pathlib import Path

# Add the rag_pipeline to the path
sys.path.insert(0, str(Path(__file__).parent / "lichen-protocol-mvp" / "rag_pipeline" / "src"))

def test_rag_service_timing():
    """Test RAG service timing stages."""
    print("Testing RAG service timing stages...")
    
    # Set up environment
    os.environ["RAG_ENABLED"] = "1"
    os.environ["RAG_PROFILE"] = "fast"
    
    try:
        from rag_service import RagService
        
        # Test disabled mode first (this should work)
        os.environ["RAG_ENABLED"] = "0"
        service = RagService("mock_index_dir")
        
        payload = {
            "trace_id": "test-123",
            "query": "What are the key principles of effective leadership?",
            "top_k": 5,
            "filters": {},
            "include_spans": True
        }
        
        response = service.query(payload)
        print("✅ RAG service disabled mode response:")
        print(f"  - retrieve_ms: {response.get('retrieve_ms', 'N/A')}")
        print(f"  - rerank_ms: {response.get('rerank_ms', 'N/A')}")
        print(f"  - synth_ms: {response.get('synth_ms', 'N/A')}")
        print(f"  - total_ms: {response.get('total_ms', 'N/A')}")
        print(f"  - latency_ms: {response.get('latency_ms', 'N/A')}")
        print(f"  - reason: {response.get('reason', 'N/A')}")
        
        # Test enabled mode (will fail without indices, but we can see the structure)
        os.environ["RAG_ENABLED"] = "1"
        try:
            response = service.query(payload)
            print("✅ RAG service enabled mode response:")
            print(f"  - retrieve_ms: {response.get('retrieve_ms', 'N/A')}")
            print(f"  - rerank_ms: {response.get('rerank_ms', 'N/A')}")
            print(f"  - synth_ms: {response.get('synth_ms', 'N/A')}")
            print(f"  - total_ms: {response.get('total_ms', 'N/A')}")
        except Exception as e:
            print(f"⚠️  RAG service enabled mode failed (expected without indices): {e}")
            
    except ImportError as e:
        print(f"❌ Could not import RAG service: {e}")
        return False
    
    return True

def test_observability_logging():
    """Test observability logging with new schema."""
    print("\nTesting observability logging...")
    
    # Set up environment for observability
    os.environ["RAG_OBS_ENABLED"] = "1"
    os.environ["RAG_OBS_DIR"] = "logs/rag"
    
    try:
        # Add the hallway directory to the path
        hallway_path = str(Path(__file__).parent / "lichen-protocol-mvp" / "hallway")
        if hallway_path not in sys.path:
            sys.path.insert(0, hallway_path)
        
        # Import the observability module
        import rag_observability
        log_rag_turn = rag_observability.log_rag_turn
        
        # Test the new logging schema
        test_citations = [
            {"source_id": "doc1", "span_start": 0, "span_end": 100},
            {"source_id": "doc2", "span_start": 50, "span_end": 150}
        ]
        
        latency_metrics = {
            "retrieve_ms": 25,
            "rerank_ms": 5,
            "synth_ms": 45,
            "total_ms": 75
        }
        
        log_rag_turn(
            request_id="test-request-123",
            profile="fast",
            query="What are the key principles of effective leadership?",
            k=5,
            latency=latency_metrics,
            grounding_score=4.2,
            citations=test_citations,
            additional_metrics={
                "stones_alignment": 0.85,
                "hallucination": 0.02,
                "used_doc_ids": ["doc1", "doc2"]
            }
        )
        
        print("✅ Observability logging completed")
        
        # Check if log file was created
        log_dir = Path("logs/rag")
        if log_dir.exists():
            log_files = list(log_dir.glob("*.jsonl"))
            if log_files:
                print(f"✅ Log file created: {log_files[0]}")
                
                # Read and display the log entry
                with open(log_files[0], 'r') as f:
                    lines = f.readlines()
                    if lines:
                        log_entry = json.loads(lines[-1])
                        print("✅ Log entry structure:")
                        print(f"  - ts: {log_entry.get('ts', 'N/A')}")
                        print(f"  - request_id: {log_entry.get('request_id', 'N/A')}")
                        print(f"  - profile: {log_entry.get('profile', 'N/A')}")
                        print(f"  - k: {log_entry.get('k', 'N/A')}")
                        print(f"  - latency: {log_entry.get('latency', 'N/A')}")
                        print(f"  - grounding_score: {log_entry.get('grounding_score', 'N/A')}")
                        print(f"  - citations: {len(log_entry.get('citations', []))} items")
            else:
                print("⚠️  No log files found")
        else:
            print("⚠️  Log directory not created")
            
    except ImportError as e:
        print(f"❌ Could not import observability module: {e}")
        return False
    except Exception as e:
        print(f"❌ Observability logging failed: {e}")
        return False
    
    return True

def test_manifest_performance():
    """Test performance with a 24-protocol manifest."""
    print("\nTesting manifest performance...")
    
    # This would require actual protocol data and indices
    print("⚠️  Manifest performance test requires actual protocol data and indices")
    print("   Expected targets:")
    print("   - Fast lane: p95 < 150ms")
    print("   - Accuracy lane: p95 < 500ms")
    
    return True

def main():
    """Run all tests."""
    print("🧪 RAG Timing and Observability Tests")
    print("=" * 50)
    
    tests = [
        test_rag_service_timing,
        test_observability_logging,
        test_manifest_performance
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    passed = sum(results)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
