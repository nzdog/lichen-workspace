#!/usr/bin/env python3
"""
Smoke test for Protocol Router implementation.

Tests basic router functionality without requiring full system setup.
"""

import sys
import os
from pathlib import Path

# Add the current directory to the path for rag module
sys.path.insert(0, str(Path(__file__).parent))
# Add the lichen-protocol-mvp directory to the path for hallway module
sys.path.insert(0, str(Path(__file__).parent / "lichen-protocol-mvp"))

def test_router_imports():
    """Test that router modules can be imported."""
    print("Testing router imports...")
    
    try:
        from rag.router import ProtocolRouter, ParsedQuery, RouteDecision, ProtocolEntry
        print("✓ Router classes imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import router classes: {e}")
        return False

def test_router_basic_functionality():
    """Test basic router functionality with mock data."""
    print("\nTesting basic router functionality...")
    
    try:
        from rag.router import ProtocolRouter, ParsedQuery, RouteDecision, ProtocolEntry
        
        # Create test config
        config = {
            "router": {
                "enabled": True,
                "k": 3,
                "min_conf_single": 0.45,
                "min_conf_double": 0.30,
                "min_conf_triple": 0.22,
                "weights": {
                    "embed": 0.6,
                    "stones": 0.2,
                    "keywords": 0.2
                }
            }
        }
        
        # Create router
        router = ProtocolRouter(config)
        print("✓ Router created successfully")
        
        # Test query parsing
        query = "leadership feels heavy / hidden load"
        parsed = router.parse_query(query)
        print(f"✓ Query parsed: {parsed.normalized_text}")
        print(f"  Stones signals: {parsed.stones_signals}")
        print(f"  Keywords: {parsed.keywords}")
        
        # Create test protocols
        test_protocols = {
            "leadership_carrying": ProtocolEntry(
                protocol_id="leadership_carrying",
                title="The Leadership I'm Actually Carrying",
                short_title="Leadership Carrying",
                stones=["stewardship", "wholeness"],
                tags=["leadership", "burden", "weight"],
                fields=["leadership", "stewardship"],
                bridges=[],
                key_phrases=["hidden load", "leadership burden", "carrying weight"]
            ),
            "pace_gate": ProtocolEntry(
                protocol_id="pace_gate",
                title="Pace Gate",
                short_title="Pace Gate",
                stones=["speed", "trust"],
                tags=["pace", "rhythm", "speed"],
                fields=["pace", "rhythm"],
                bridges=[],
                key_phrases=["rushing", "pace adjustment", "rhythm"]
            )
        }
        
        router.catalog = test_protocols
        print("✓ Test protocols loaded")
        
        # Test routing
        decision = router._route_keywords_only(parsed, k=3)
        print(f"✓ Routing completed: {decision.route} (confidence: {decision.confidence:.3f})")
        
        if decision.candidates:
            print(f"  Top candidate: {decision.candidates[0]['protocol_id']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Router functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rag_adapter_integration():
    """Test RAG adapter integration."""
    print("\nTesting RAG adapter integration...")
    
    try:
        from hallway.adapters.rag_adapter import RAGAdapter
        print("✓ RAG adapter imported successfully")
        
        # Test that retrieve method accepts use_router parameter
        adapter = RAGAdapter()
        
        # Check if the method signature includes use_router
        import inspect
        sig = inspect.signature(adapter.retrieve)
        if 'use_router' in sig.parameters:
            print("✓ RAG adapter retrieve method supports use_router parameter")
            return True
        else:
            print("✗ RAG adapter retrieve method missing use_router parameter")
            return False
            
    except Exception as e:
        print(f"✗ RAG adapter integration test failed: {e}")
        return False

def test_config_files():
    """Test that configuration files exist and are valid."""
    print("\nTesting configuration files...")
    
    config_files = [
        "lichen-protocol-mvp/config/rag.yaml",
        "config/models.yaml"
    ]
    
    all_good = True
    
    for config_file in config_files:
        if Path(config_file).exists():
            print(f"✓ {config_file} exists")
            
            # Try to load as YAML
            try:
                import yaml
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                if config_file.endswith("rag.yaml"):
                    if "router" in config:
                        print(f"  ✓ Router configuration found")
                    else:
                        print(f"  ✗ Router configuration missing")
                        all_good = False
                
            except Exception as e:
                print(f"  ✗ Failed to load {config_file}: {e}")
                all_good = False
        else:
            print(f"✗ {config_file} not found")
            all_good = False
    
    return all_good

def main():
    """Run all smoke tests."""
    print("Protocol Router Smoke Test")
    print("=" * 40)
    
    tests = [
        test_router_imports,
        test_router_basic_functionality,
        test_rag_adapter_integration,
        test_config_files
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\nSmoke Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Router implementation is ready.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
