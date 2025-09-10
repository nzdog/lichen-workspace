#!/usr/bin/env python3
"""
Test script to verify all demo scenarios work correctly
"""

import asyncio
import sys
from demo import LichenDemo
from web_demo import WebDemo


async def test_cli_demo():
    """Test the CLI demo scenarios"""
    print("🧪 Testing CLI Demo Scenarios...")
    demo = LichenDemo()
    
    scenarios = [
        ("Full Canonical Walk", demo.run_full_canonical_walk),
        ("Mini Walk", demo.run_mini_walk),
        ("Custom Subset", demo.run_custom_subset),
        ("Dry Run", demo.run_dry_run),
        ("Gate Deny", demo.run_gate_deny),
    ]
    
    results = {}
    
    for name, func in scenarios:
        print(f"\n  Testing {name}...")
        try:
            result = await func()
            completed = result["outputs"]["exit_summary"]["completed"]
            steps = len(result["outputs"]["steps"])
            results[name] = {"completed": completed, "steps": steps, "success": True}
            print(f"    ✅ {name}: Completed={completed}, Steps={steps}")
        except Exception as e:
            results[name] = {"error": str(e), "success": False}
            print(f"    ❌ {name}: Error - {e}")
    
    return results


async def test_web_demo():
    """Test the web demo scenarios"""
    print("\n🧪 Testing Web Demo Scenarios...")
    demo = WebDemo()
    
    scenarios = [
        ("Full Canonical Walk", demo.run_full_canonical_walk),
        ("Mini Walk", demo.run_mini_walk),
        ("Custom Subset", demo.run_custom_subset),
        ("Dry Run", demo.run_dry_run),
        ("Gate Deny", demo.run_gate_deny),
    ]
    
    results = {}
    
    for name, func in scenarios:
        print(f"\n  Testing {name}...")
        try:
            result = await func()
            completed = result["outputs"]["exit_summary"]["completed"]
            steps = len(result["outputs"]["steps"])
            results[name] = {"completed": completed, "steps": steps, "success": True}
            print(f"    ✅ {name}: Completed={completed}, Steps={steps}")
        except Exception as e:
            results[name] = {"error": str(e), "success": False}
            print(f"    ❌ {name}: Error - {e}")
    
    return results


def verify_expected_results(results, demo_type):
    """Verify that results match expected outcomes"""
    print(f"\n📊 Verifying {demo_type} Results...")
    
    expected = {
        "Full Canonical Walk": {"completed": True, "steps": 7},
        "Mini Walk": {"completed": True, "steps": 2},
        "Custom Subset": {"completed": True, "steps": 3},
        "Dry Run": {"completed": True, "steps": 7},
        "Gate Deny": {"completed": False, "steps": 2},
    }
    
    all_passed = True
    
    for scenario, expected_result in expected.items():
        if scenario in results:
            result = results[scenario]
            if result["success"]:
                if (result["completed"] == expected_result["completed"] and 
                    result["steps"] == expected_result["steps"]):
                    print(f"  ✅ {scenario}: PASS")
                else:
                    print(f"  ❌ {scenario}: FAIL - Expected {expected_result}, got {result}")
                    all_passed = False
            else:
                print(f"  ❌ {scenario}: ERROR - {result['error']}")
                all_passed = False
        else:
            print(f"  ❌ {scenario}: MISSING")
            all_passed = False
    
    return all_passed


async def main():
    """Main test function"""
    print("🧬 Lichen Protocol SIS MVP Demo Test Suite")
    print("=" * 60)
    
    # Test CLI demo
    cli_results = await test_cli_demo()
    cli_passed = verify_expected_results(cli_results, "CLI Demo")
    
    # Test web demo
    web_results = await test_web_demo()
    web_passed = verify_expected_results(web_results, "Web Demo")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    print(f"CLI Demo: {'✅ PASS' if cli_passed else '❌ FAIL'}")
    print(f"Web Demo: {'✅ PASS' if web_passed else '❌ FAIL'}")
    
    if cli_passed and web_passed:
        print("\n🎉 All demo scenarios working correctly!")
        print("✅ Full Canonical Walk → Completed: True, 7 steps")
        print("✅ Mini Walk → Completed: True, 2 steps")
        print("✅ Custom Subset → Completed: True, 3 steps")
        print("✅ Dry Run → all rooms available")
        print("✅ Gate Deny → Completed: False with decline reason")
        return 0
    else:
        print("\n❌ Some demo scenarios failed!")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        sys.exit(1)
