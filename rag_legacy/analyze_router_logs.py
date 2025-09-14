#!/usr/bin/env python3
"""
Analyze router decision logs to understand routing patterns.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

def analyze_router_logs(log_file_path: str):
    """Analyze router decision logs and print statistics."""

    if not Path(log_file_path).exists():
        print(f"❌ Log file not found: {log_file_path}")
        return

    decisions = []

    # Load all decisions
    with open(log_file_path, 'r') as f:
        for line in f:
            try:
                decision = json.loads(line.strip())
                decisions.append(decision)
            except json.JSONDecodeError:
                continue

    if not decisions:
        print(f"❌ No valid decisions found in {log_file_path}")
        return

    total_decisions = len(decisions)

    # Route distribution
    route_counts = Counter(d['route'] for d in decisions)
    routing_active = sum(1 for d in decisions if d.get('routing_active', False))
    fallback_count = sum(1 for d in decisions if d['route'] == 'all')

    print("🎯 ROUTER DECISION ANALYSIS")
    print("=" * 50)
    print(f"Total queries: {total_decisions}")
    print(f"Active routing: {routing_active} ({routing_active/total_decisions*100:.1f}%)")
    print(f"Fallback to all: {fallback_count} ({fallback_count/total_decisions*100:.1f}%)")
    print()

    # Route type breakdown
    print("📊 ROUTE TYPE DISTRIBUTION")
    for route, count in route_counts.most_common():
        pct = count / total_decisions * 100
        print(f"  {route:8s}: {count:3d} ({pct:5.1f}%)")
    print()

    # Confidence analysis
    confidences = [d['confidence'] for d in decisions]
    avg_confidence = sum(confidences) / len(confidences)

    confidence_ranges = {
        "Very High (>0.5)": sum(1 for c in confidences if c > 0.5),
        "High (0.35-0.5)": sum(1 for c in confidences if 0.35 <= c <= 0.5),
        "Medium (0.25-0.35)": sum(1 for c in confidences if 0.25 <= c < 0.35),
        "Low (0.18-0.25)": sum(1 for c in confidences if 0.18 <= c < 0.25),
        "Very Low (<0.18)": sum(1 for c in confidences if c < 0.18)
    }

    print("🎯 CONFIDENCE ANALYSIS")
    print(f"Average confidence: {avg_confidence:.3f}")
    for range_name, count in confidence_ranges.items():
        if count > 0:
            pct = count / total_decisions * 100
            print(f"  {range_name}: {count:3d} ({pct:5.1f}%)")
    print()

    # Protocol selection patterns
    protocol_selections = Counter()
    for decision in decisions:
        if decision.get('routing_active', False):
            for candidate in decision.get('candidates', []):
                protocol_id = candidate.get('protocol_id', 'unknown')
                protocol_selections[protocol_id] += 1

    print("🔍 TOP SELECTED PROTOCOLS")
    for protocol, count in protocol_selections.most_common(10):
        print(f"  {protocol[:40]:40s}: {count:3d}")
    print()

    # Stones analysis
    stones_usage = Counter()
    for decision in decisions:
        for stone in decision.get('stones_signals', []):
            stones_usage[stone] += 1

    print("🪨 STONES SIGNAL USAGE")
    for stone, count in stones_usage.most_common():
        pct = count / total_decisions * 100
        print(f"  {stone:20s}: {count:3d} ({pct:5.1f}%)")
    print()

    # Routing effectiveness by confidence
    print("⚡ ROUTING EFFECTIVENESS")
    high_conf_routing = sum(1 for d in decisions if d['confidence'] >= 0.35 and d.get('routing_active', False))
    medium_conf_routing = sum(1 for d in decisions if 0.25 <= d['confidence'] < 0.35 and d.get('routing_active', False))
    low_conf_routing = sum(1 for d in decisions if 0.18 <= d['confidence'] < 0.25 and d.get('routing_active', False))

    total_high_conf = sum(1 for d in decisions if d['confidence'] >= 0.35)
    total_medium_conf = sum(1 for d in decisions if 0.25 <= d['confidence'] < 0.35)
    total_low_conf = sum(1 for d in decisions if 0.18 <= d['confidence'] < 0.25)

    if total_high_conf > 0:
        print(f"  High confidence queries that route: {high_conf_routing}/{total_high_conf} ({high_conf_routing/total_high_conf*100:.1f}%)")
    if total_medium_conf > 0:
        print(f"  Medium confidence queries that route: {medium_conf_routing}/{total_medium_conf} ({medium_conf_routing/total_medium_conf*100:.1f}%)")
    if total_low_conf > 0:
        print(f"  Low confidence queries that route: {low_conf_routing}/{total_low_conf} ({low_conf_routing/total_low_conf*100:.1f}%)")

if __name__ == "__main__":
    log_path = "logs/router_decisions.jsonl"
    if len(sys.argv) > 1:
        log_path = sys.argv[1]

    analyze_router_logs(log_path)