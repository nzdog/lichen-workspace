#!/usr/bin/env python3
"""
Generate a formatted summary table for RAG evaluation results.

This script creates a markdown table showing key metrics for both lanes
with comparison to baseline values when available.
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Any, Optional


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


def format_metric_value(value: float, metric_name: str) -> str:
    """Format a metric value for display."""
    if metric_name in ['latency_ms_p95']:
        return f"{value:.1f}"
    elif metric_name in ['precision_at_5', 'recall_at_20', 'mrr_at_10', 'ndcg_at_10', 
                        'coverage', 'stones_alignment', 'hallucination_rate']:
        return f"{value:.3f}"
    elif metric_name in ['diversity_avg_top8', 'grounding_1to5']:
        return f"{value:.1f}"
    else:
        return f"{value:.3f}"


def get_delta_indicator(current: float, baseline: float, higher_is_better: bool = True) -> str:
    """Get a delta indicator (↗️, ↘️, ➡️) based on change from baseline."""
    delta = current - baseline
    if abs(delta) < 0.001:  # Essentially no change
        return "➡️"
    elif (delta > 0 and higher_is_better) or (delta < 0 and not higher_is_better):
        return "↗️"  # Improvement
    else:
        return "↘️"  # Regression


def generate_metrics_table(fast_summary: Dict[str, Any], accurate_summary: Dict[str, Any],
                          fast_baseline: Optional[Dict[str, Any]] = None,
                          accurate_baseline: Optional[Dict[str, Any]] = None) -> str:
    """Generate a markdown table of key metrics."""
    
    # Define key metrics to display
    key_metrics = [
        ('precision_at_5', 'Precision@5', True),
        ('recall_at_20', 'Recall@20', True),
        ('mrr_at_10', 'MRR@10', True),
        ('ndcg_at_10', 'nDCG@10', True),
        ('coverage', 'Coverage', True),
        ('latency_ms_p95', 'Latency p95 (ms)', False),
        ('diversity_avg_top8', 'Diversity (top-8)', True),
        ('stones_alignment', 'Stones Alignment', True),
        ('grounding_1to5', 'Grounding (1-5)', True),
        ('hallucination_rate', 'Hallucination Rate', False),
    ]
    
    lines = []
    lines.append("| Metric | Fast Lane | Accurate Lane |")
    lines.append("|--------|-----------|---------------|")
    
    for metric_key, metric_name, higher_is_better in key_metrics:
        fast_value = fast_summary.get(metric_key, 0)
        accurate_value = accurate_summary.get(metric_key, 0)
        
        # Format values
        fast_str = format_metric_value(fast_value, metric_key)
        accurate_str = format_metric_value(accurate_value, metric_key)
        
        # Add baseline comparison if available
        if fast_baseline and metric_key in fast_baseline:
            baseline_value = fast_baseline[metric_key]
            delta_indicator = get_delta_indicator(fast_value, baseline_value, higher_is_better)
            fast_str = f"{fast_str} {delta_indicator}"
        
        if accurate_baseline and metric_key in accurate_baseline:
            baseline_value = accurate_baseline[metric_key]
            delta_indicator = get_delta_indicator(accurate_value, baseline_value, higher_is_better)
            accurate_str = f"{accurate_str} {delta_indicator}"
        
        lines.append(f"| {metric_name} | {fast_str} | {accurate_str} |")
    
    return "\n".join(lines)


def generate_summary_stats(fast_summary: Dict[str, Any], accurate_summary: Dict[str, Any]) -> str:
    """Generate summary statistics."""
    lines = []
    
    lines.append("### 📈 Summary Statistics")
    lines.append("")
    lines.append(f"- **Total Queries Evaluated**: {fast_summary.get('num_queries', 0)}")
    lines.append(f"- **Fast Lane Latency p95**: {fast_summary.get('latency_ms_p95', 0):.1f}ms")
    lines.append(f"- **Accurate Lane Latency p95**: {accurate_summary.get('latency_ms_p95', 0):.1f}ms")
    lines.append("")
    
    # Performance indicators
    fast_coverage = fast_summary.get('coverage', 0)
    accurate_coverage = accurate_summary.get('coverage', 0)
    
    if fast_coverage >= 0.95 and accurate_coverage >= 0.95:
        lines.append("✅ **Coverage targets met** for both lanes")
    else:
        lines.append("⚠️ **Coverage below target** (95%) for one or both lanes")
    
    lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate RAG evaluation summary")
    parser.add_argument("--fast-summary", required=True,
                       help="Path to fast lane summary JSON")
    parser.add_argument("--accurate-summary", required=True,
                       help="Path to accurate lane summary JSON")
    parser.add_argument("--baseline-dir", 
                       help="Directory containing baseline summary files")
    parser.add_argument("--output-format", choices=['markdown', 'text'], default='markdown',
                       help="Output format (default: markdown)")
    
    args = parser.parse_args()
    
    try:
        fast_summary = load_summary(args.fast_summary)
        accurate_summary = load_summary(args.accurate_summary)
    except Exception as e:
        print(f"Error loading summaries: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Load baselines if available
    fast_baseline = None
    accurate_baseline = None
    
    if args.baseline_dir and os.path.exists(args.baseline_dir):
        fast_baseline = get_baseline_summary(args.baseline_dir, 'fast')
        accurate_baseline = get_baseline_summary(args.baseline_dir, 'accurate')
    
    # Generate output
    if args.output_format == 'markdown':
        print("### 🎯 Key Metrics")
        print("")
        print(generate_metrics_table(fast_summary, accurate_summary, fast_baseline, accurate_baseline))
        print("")
        print(generate_summary_stats(fast_summary, accurate_summary))
        
        # Add legend
        print("### 📊 Legend")
        print("")
        print("- ↗️ Improvement from baseline")
        print("- ↘️ Regression from baseline") 
        print("- ➡️ No significant change from baseline")
        print("")
    else:
        # Text format
        print("RAG Evaluation Results:")
        print("=" * 50)
        print(f"Fast Lane - Queries: {fast_summary.get('num_queries', 0)}")
        print(f"  Coverage: {fast_summary.get('coverage', 0):.3f}")
        print(f"  Recall@20: {fast_summary.get('recall_at_20', 0):.3f}")
        print(f"  nDCG@10: {fast_summary.get('ndcg_at_10', 0):.3f}")
        print(f"  Latency p95: {fast_summary.get('latency_ms_p95', 0):.1f}ms")
        print()
        print(f"Accurate Lane - Queries: {accurate_summary.get('num_queries', 0)}")
        print(f"  Coverage: {accurate_summary.get('coverage', 0):.3f}")
        print(f"  Recall@20: {accurate_summary.get('recall_at_20', 0):.3f}")
        print(f"  nDCG@10: {accurate_summary.get('ndcg_at_10', 0):.3f}")
        print(f"  Latency p95: {accurate_summary.get('latency_ms_p95', 0):.1f}ms")


if __name__ == "__main__":
    main()
