"""
Generate router decisions analysis from evaluation results.

Extracts router decisions from evaluation records and creates CSV for analysis.
"""

import json
import csv
import argparse
from pathlib import Path
from typing import List, Dict, Any


def extract_router_decisions(records_file: str) -> List[Dict[str, Any]]:
    """Extract router decisions from evaluation records."""
    decisions = []
    
    with open(records_file, 'r') as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                
                # Extract router decision if available
                if "router_decision" in record:
                    router_decision = record["router_decision"]
                    
                    decision = {
                        "query_id": record.get("query_id", "unknown"),
                        "query": record.get("query", ""),
                        "lane": record.get("lane", "unknown"),
                        "use_router": record.get("use_router", False),
                        "route": router_decision.get("route", "unknown"),
                        "confidence": router_decision.get("confidence", 0.0),
                        "candidates": json.dumps(router_decision.get("candidates", [])),
                        "candidate_count": len(router_decision.get("candidates", [])),
                        "top_candidate_id": router_decision.get("candidates", [{}])[0].get("protocol_id", "") if router_decision.get("candidates") else "",
                        "top_candidate_title": router_decision.get("candidates", [{}])[0].get("title", "") if router_decision.get("candidates") else "",
                        "top_candidate_score": router_decision.get("candidates", [{}])[0].get("score", 0.0) if router_decision.get("candidates") else 0.0
                    }
                    
                    decisions.append(decision)
    
    return decisions


def save_router_decisions_csv(decisions: List[Dict[str, Any]], output_file: str):
    """Save router decisions to CSV file."""
    if not decisions:
        print("No router decisions found to save")
        return
    
    fieldnames = [
        "query_id", "query", "lane", "use_router", "route", "confidence",
        "candidate_count", "top_candidate_id", "top_candidate_title", "top_candidate_score", "candidates"
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(decisions)
    
    print(f"Saved {len(decisions)} router decisions to {output_file}")


def analyze_router_performance(decisions: List[Dict[str, Any]]):
    """Analyze router performance and print summary."""
    if not decisions:
        print("No router decisions to analyze")
        return
    
    # Group by lane
    by_lane = {}
    for decision in decisions:
        lane = decision["lane"]
        if lane not in by_lane:
            by_lane[lane] = []
        by_lane[lane].append(decision)
    
    print("\nRouter Performance Analysis")
    print("=" * 50)
    
    for lane, lane_decisions in by_lane.items():
        print(f"\n{lane.upper()} Lane:")
        print(f"  Total queries: {len(lane_decisions)}")
        
        # Route distribution
        route_counts = {}
        confidence_sum = 0.0
        high_confidence_count = 0
        
        for decision in lane_decisions:
            route = decision["route"]
            confidence = decision["confidence"]
            
            route_counts[route] = route_counts.get(route, 0) + 1
            confidence_sum += confidence
            
            if confidence >= 0.45:  # High confidence threshold
                high_confidence_count += 1
        
        print(f"  Route distribution:")
        for route, count in sorted(route_counts.items()):
            percentage = (count / len(lane_decisions)) * 100
            print(f"    {route}: {count} ({percentage:.1f}%)")
        
        avg_confidence = confidence_sum / len(lane_decisions)
        high_conf_percentage = (high_confidence_count / len(lane_decisions)) * 100
        
        print(f"  Average confidence: {avg_confidence:.3f}")
        print(f"  High confidence (≥0.45): {high_confidence_count} ({high_conf_percentage:.1f}%)")
        
        # Top protocols
        protocol_counts = {}
        for decision in lane_decisions:
            if decision["top_candidate_id"]:
                protocol_id = decision["top_candidate_id"]
                protocol_counts[protocol_id] = protocol_counts.get(protocol_id, 0) + 1
        
        if protocol_counts:
            print(f"  Top routed protocols:")
            sorted_protocols = sorted(protocol_counts.items(), key=lambda x: x[1], reverse=True)
            for protocol_id, count in sorted_protocols[:5]:
                percentage = (count / len(lane_decisions)) * 100
                print(f"    {protocol_id}: {count} ({percentage:.1f}%)")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate router decisions analysis")
    parser.add_argument("--records", required=True, help="Path to evaluation records JSONL file")
    parser.add_argument("--output", default="eval/out/router_decisions.csv", help="Output CSV file")
    parser.add_argument("--analyze", action="store_true", help="Print performance analysis")
    
    args = parser.parse_args()
    
    # Extract router decisions
    print(f"Extracting router decisions from {args.records}...")
    decisions = extract_router_decisions(args.records)
    
    if not decisions:
        print("No router decisions found in records file")
        return
    
    # Save to CSV
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_router_decisions_csv(decisions, str(output_path))
    
    # Analyze performance if requested
    if args.analyze:
        analyze_router_performance(decisions)


if __name__ == "__main__":
    main()
