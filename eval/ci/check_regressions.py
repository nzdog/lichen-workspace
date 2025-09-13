#!/usr/bin/env python3
"""
Check for regressions in RAG evaluation metrics by comparing current results to baseline.

This script compares key metrics (coverage, recall_at_20, ndcg_at_10) between current
and baseline evaluation results, flagging regressions beyond the specified tolerance.
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Any, Optional, Tuple


def load_summary(summary_path: str) -> Dict[str, Any]:
    """Load evaluation summary from JSON file."""
    if not os.path.exists(summary_path):
        raise FileNotFoundError(f"Summary file not found: {summary_path}")
    
    with open(summary_path, 'r') as f:
        return json.load(f)


def get_baseline_summary(baseline_dir: str, lane: str) -> Optional[Dict[str, Any]]:
    """Get baseline summary for a lane, returning None if not found."""
    baseline_path = os.path.join(baseline_dir, f"summary_{lane}.json")
    if not os.path.exists(baseline_path):
        return None
    
    try:
        return load_summary(baseline_path)
    except Exception as e:
        print(f"Warning: Could not load baseline for {lane}: {e}", file=sys.stderr)
        return None


def compare_metrics(current: Dict[str, Any], baseline: Dict[str, Any], 
                   tolerance: float) -> List[Dict[str, Any]]:
    """
    Compare metrics between current and baseline results.
    
    Returns list of regressions found.
    """
    regressions = []
    
    # Key metrics to check for regressions
    key_metrics = [
        ('coverage', True),  # (metric_name, higher_is_better)
        ('recall_at_20', True),
        ('ndcg_at_10', True),
    ]
    
    for metric_name, higher_is_better in key_metrics:
        if metric_name not in current:
            continue
            
        current_value = current[metric_name]
        baseline_value = baseline.get(metric_name)
        
        if baseline_value is None:
            continue
        
        # Calculate delta
        delta = current_value - baseline_value
        
        # Check for regression
        is_regression = False
        if higher_is_better:
            # For metrics where higher is better, regression is significant decrease
            is_regression = delta < -tolerance
        else:
            # For metrics where lower is better (like latency), regression is significant increase
            is_regression = delta > tolerance
        
        if is_regression:
            regressions.append({
                'metric': metric_name,
                'current_value': current_value,
                'baseline_value': baseline_value,
                'delta': delta,
                'tolerance': tolerance,
                'higher_is_better': higher_is_better
            })
    
    return regressions


def check_lane_regressions(current_path: str, baseline_dir: str, lane: str, 
                          tolerance: float) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Check for regressions in a specific lane.
    
    Returns:
        (has_regressions, list_of_regressions)
    """
    try:
        current = load_summary(current_path)
    except Exception as e:
        print(f"Error loading current summary for {lane}: {e}", file=sys.stderr)
        return False, []
    
    baseline = get_baseline_summary(baseline_dir, lane)
    if baseline is None:
        print(f"No baseline found for {lane} lane - skipping regression check", file=sys.stderr)
        return False, []
    
    regressions = compare_metrics(current, baseline, tolerance)
    
    # Add lane information to each regression
    for regression in regressions:
        regression['lane'] = lane
    
    return len(regressions) > 0, regressions


def main():
    parser = argparse.ArgumentParser(description="Check for RAG evaluation regressions")
    parser.add_argument("--current-fast", required=True,
                       help="Path to current fast lane summary JSON")
    parser.add_argument("--current-accurate", required=True,
                       help="Path to current accurate lane summary JSON")
    parser.add_argument("--baseline-dir", required=True,
                       help="Directory containing baseline summary files")
    parser.add_argument("--tolerance", type=float, default=0.01,
                       help="Tolerance for regression detection (default: 0.01)")
    parser.add_argument("--output-format", choices=['json', 'text'], default='text',
                       help="Output format (default: text)")
    
    args = parser.parse_args()
    
    all_regressions = []
    has_any_regressions = False
    
    # Check both lanes
    for lane, current_path in [('fast', args.current_fast), ('accurate', args.current_accurate)]:
        has_regressions, regressions = check_lane_regressions(
            current_path, args.baseline_dir, lane, args.tolerance
        )
        
        if has_regressions:
            has_any_regressions = True
            all_regressions.extend(regressions)
    
    # Output results
    if args.output_format == 'json':
        result = {
            'has_regressions': has_any_regressions,
            'tolerance': args.tolerance,
            'regressions': all_regressions
        }
        print(json.dumps(result, indent=2))
    else:
        if has_any_regressions:
            print("❌ REGRESSIONS DETECTED")
            print(f"Tolerance: {args.tolerance}")
            print()
            
            for regression in all_regressions:
                lane = regression['lane']
                metric = regression['metric']
                current = regression['current_value']
                baseline = regression['baseline_value']
                delta = regression['delta']
                
                print(f"{lane.upper()} lane - {metric}:")
                print(f"  Current:  {current:.3f}")
                print(f"  Baseline: {baseline:.3f}")
                print(f"  Delta:    {delta:+.3f}")
                print()
        else:
            print("✅ No regressions detected")
    
    # Exit with error code if regressions found
    if has_any_regressions:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
