#!/usr/bin/env python3
"""
Validate router decisions by checking if routed protocols are actually relevant to queries.
"""

import json
import sys
import os
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple
import re

def load_protocol_data(protocols_dir: str = "protocols") -> Dict[str, Dict]:
    """Load actual protocol content for validation."""
    protocols = {}

    protocols_path = Path(protocols_dir)
    if not protocols_path.exists():
        print(f"❌ Protocols directory not found: {protocols_dir}")
        return {}

    for protocol_file in protocols_path.glob("*.json"):
        try:
            with open(protocol_file, 'r') as f:
                protocol_data = json.load(f)
                # Use Protocol ID field if available, otherwise use filename
                protocol_id = protocol_data.get('Protocol ID', protocol_data.get('id', protocol_file.stem))
                protocols[protocol_id] = protocol_data
        except Exception as e:
            print(f"⚠️ Error loading {protocol_file}: {e}")
            continue

    print(f"📚 Loaded {len(protocols)} protocols from {protocols_dir}")
    return protocols

def extract_protocol_text(protocol_data: Dict) -> str:
    """Extract searchable text from protocol for relevance checking."""
    text_parts = []

    # Title and short title (using actual field names)
    if 'Title' in protocol_data:
        text_parts.append(protocol_data['Title'])
    if 'Short Title' in protocol_data:
        text_parts.append(protocol_data['Short Title'])

    # Purpose and description fields
    if 'Overall Purpose' in protocol_data:
        text_parts.append(protocol_data['Overall Purpose'])
    if 'Why This Matters' in protocol_data:
        text_parts.append(protocol_data['Why This Matters'])
    if 'When To Use This Protocol' in protocol_data:
        text_parts.append(protocol_data['When To Use This Protocol'])

    # Outcomes
    if 'Overall Outcomes' in protocol_data and isinstance(protocol_data['Overall Outcomes'], dict):
        for outcome_type, outcome_text in protocol_data['Overall Outcomes'].items():
            text_parts.append(str(outcome_text))

    # Themes
    if 'Themes' in protocol_data and isinstance(protocol_data['Themes'], list):
        for theme in protocol_data['Themes']:
            if isinstance(theme, dict):
                if 'Name' in theme:
                    text_parts.append(theme['Name'])
                if 'Purpose of This Theme' in theme:
                    text_parts.append(theme['Purpose of This Theme'])
                if 'Why This Matters' in theme:
                    text_parts.append(theme['Why This Matters'])

    # Metadata fields
    if 'Metadata' in protocol_data and isinstance(protocol_data['Metadata'], dict):
        metadata = protocol_data['Metadata']
        if 'Stones' in metadata:
            if isinstance(metadata['Stones'], list):
                text_parts.extend(metadata['Stones'])
        if 'Fields' in metadata:
            if isinstance(metadata['Fields'], list):
                text_parts.extend(metadata['Fields'])
        if 'Tags' in metadata:
            if isinstance(metadata['Tags'], list):
                text_parts.extend(metadata['Tags'])

    return ' '.join(text_parts).lower()

def calculate_relevance_score(query: str, protocol_text: str, protocol_id: str) -> float:
    """Calculate relevance score between query and protocol."""
    if not protocol_text.strip():
        return 0.0

    query_lower = query.lower()
    protocol_lower = protocol_text.lower()

    # 1. Exact phrase matches (high weight)
    query_words = query_lower.split()
    exact_matches = 0
    for i in range(len(query_words) - 1):
        phrase = f"{query_words[i]} {query_words[i+1]}"
        if phrase in protocol_lower:
            exact_matches += 1

    # 2. Individual word matches
    word_matches = sum(1 for word in query_words if len(word) > 3 and word in protocol_lower)

    # 3. Protocol ID readability bonus (human-readable names are better)
    readable_bonus = 0.1 if not re.match(r'^auto_\d+_\d+$', protocol_id) else 0.0

    # 4. Title/theme matches (higher weight)
    title_matches = 0
    if 'title' in protocol_text or 'theme' in protocol_text:
        title_section = protocol_text[:200]  # First 200 chars likely contain title
        title_matches = sum(0.5 for word in query_words if len(word) > 3 and word in title_section)

    # Combined score
    relevance = (
        exact_matches * 0.4 +
        word_matches * 0.3 +
        title_matches * 0.2 +
        readable_bonus
    ) / max(len(query_words), 1)

    return min(relevance, 1.0)

def validate_router_decisions(log_file_path: str, protocols_dir: str = "protocols"):
    """Validate router decisions against actual protocol content."""

    if not Path(log_file_path).exists():
        print(f"❌ Log file not found: {log_file_path}")
        return

    # Load protocol data
    protocols = load_protocol_data(protocols_dir)
    if not protocols:
        return

    decisions = []

    # Load router decisions
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

    print(f"\n🔍 PROTOCOL RELEVANCE VALIDATION")
    print("=" * 50)
    print(f"Analyzing {len(decisions)} router decisions...")

    # Debug: Check how many have candidates and are active
    routed_decisions = [d for d in decisions if d.get('candidates') and d.get('routing_active', False)]
    print(f"DEBUG: Found {len(routed_decisions)} routed decisions with candidates")

    # Validation metrics
    total_relevance = 0.0
    high_relevance_count = 0
    medium_relevance_count = 0
    low_relevance_count = 0
    missing_protocols = set()

    relevance_by_route = defaultdict(list)
    false_positives = []
    good_matches = []

    print(f"\n📊 DETAILED VALIDATION RESULTS")
    print("-" * 50)

    for i, decision in enumerate(routed_decisions[:10]):  # Show first 10 routed decisions for detailed analysis
        query = decision.get('query', '').strip()
        candidates = decision.get('candidates', [])
        route = decision.get('route', 'unknown')
        confidence = decision.get('confidence', 0.0)

        print(f"\n{i+1:2d}. Query: '{query[:60]}{'...' if len(query) > 60 else ''}'")
        print(f"    Route: {route} | Confidence: {confidence:.3f}")

        for j, candidate in enumerate(candidates[:2]):  # Show top 2 candidates
            protocol_id = candidate.get('protocol_id', 'unknown')
            router_score = candidate.get('score', 0.0)

            if protocol_id in protocols:
                protocol_text = extract_protocol_text(protocols[protocol_id])
                relevance = calculate_relevance_score(query, protocol_text, protocol_id)

                total_relevance += relevance
                if relevance >= 0.3:
                    high_relevance_count += 1
                    good_matches.append((query, protocol_id, relevance, router_score))
                elif relevance >= 0.15:
                    medium_relevance_count += 1
                else:
                    low_relevance_count += 1
                    false_positives.append((query, protocol_id, relevance, router_score))

                relevance_by_route[route].append(relevance)

                # Display result
                relevance_emoji = "🟢" if relevance >= 0.3 else "🟡" if relevance >= 0.15 else "🔴"
                protocol_title = protocols[protocol_id].get('title', protocol_id)[:40]
                print(f"    {j+1}. {relevance_emoji} {protocol_id[:25]:25s} | Relevance: {relevance:.3f} | Title: {protocol_title}")

            else:
                missing_protocols.add(protocol_id)
                print(f"    {j+1}. ❓ {protocol_id} (not found in protocols)")

    # Summary statistics
    total_candidates = sum(len(d.get('candidates', [])) for d in routed_decisions)
    avg_relevance = total_relevance / max(total_candidates, 1)

    print(f"\n📈 RELEVANCE SUMMARY")
    print("-" * 30)
    print(f"Average relevance: {avg_relevance:.3f}")
    print(f"High relevance (≥0.3): {high_relevance_count} ({high_relevance_count/total_candidates*100:.1f}%)")
    print(f"Medium relevance (0.15-0.3): {medium_relevance_count} ({medium_relevance_count/total_candidates*100:.1f}%)")
    print(f"Low relevance (<0.15): {low_relevance_count} ({low_relevance_count/total_candidates*100:.1f}%)")

    if missing_protocols:
        print(f"Missing protocols: {len(missing_protocols)}")

    # Route-specific analysis
    print(f"\n🎯 RELEVANCE BY ROUTE TYPE")
    print("-" * 30)
    for route, scores in relevance_by_route.items():
        if scores:
            avg_score = sum(scores) / len(scores)
            print(f"{route:8s}: {avg_score:.3f} (n={len(scores)})")

    # False positives (potential routing errors)
    if false_positives:
        print(f"\n🚨 POTENTIAL FALSE POSITIVES (Top 5)")
        print("-" * 40)
        false_positives.sort(key=lambda x: x[2])  # Sort by relevance (lowest first)
        for i, (query, protocol_id, relevance, router_score) in enumerate(false_positives[:5]):
            print(f"{i+1}. '{query[:40]}...' → {protocol_id[:25]}")
            print(f"   Relevance: {relevance:.3f} | Router Score: {router_score:.3f}")

    # Good matches (validation that router works)
    if good_matches:
        print(f"\n✅ BEST ROUTING DECISIONS (Top 5)")
        print("-" * 40)
        good_matches.sort(key=lambda x: x[2], reverse=True)  # Sort by relevance (highest first)
        for i, (query, protocol_id, relevance, router_score) in enumerate(good_matches[:5]):
            protocol_title = protocols.get(protocol_id, {}).get('title', protocol_id)[:30]
            print(f"{i+1}. '{query[:30]}...' → {protocol_title}")
            print(f"   Relevance: {relevance:.3f} | Router Score: {router_score:.3f}")

if __name__ == "__main__":
    log_path = "logs/router_decisions.jsonl"
    protocols_dir = "protocols"

    if len(sys.argv) > 1:
        log_path = sys.argv[1]
    if len(sys.argv) > 2:
        protocols_dir = sys.argv[2]

    validate_router_decisions(log_path, protocols_dir)