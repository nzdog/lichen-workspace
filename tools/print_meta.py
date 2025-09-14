#!/usr/bin/env python3
"""
Helper script to print metadata from FAISS indices.

Usage:
    python tools/print_meta.py --lane fast --grep "pace"
    python tools/print_meta.py --lane accurate --grep "mirror"
"""

import argparse
import json
import sys
from pathlib import Path


def load_metadata(lane: str) -> list:
    """Load metadata for the specified lane."""
    meta_path = f".vector/{lane}.meta.jsonl"
    
    if not Path(meta_path).exists():
        print(f"Error: Metadata file not found: {meta_path}")
        sys.exit(1)
    
    metadata = []
    with open(meta_path, 'r') as f:
        for line in f:
            if line.strip():
                metadata.append(json.loads(line))
    
    return metadata


def print_metadata(metadata: list, grep_term: str = None, limit: int = 10):
    """Print metadata with optional filtering."""
    filtered_metadata = metadata
    
    if grep_term:
        filtered_metadata = [
            meta for meta in metadata
            if grep_term.lower() in meta.get("text", "").lower()
        ]
    
    print(f"Found {len(filtered_metadata)} documents (showing first {limit})")
    print("=" * 80)
    
    for i, meta in enumerate(filtered_metadata[:limit]):
        print(f"Document {i+1}:")
        print(f"  ID: {meta.get('vector_id', 'unknown')}")
        print(f"  Doc: {meta.get('doc', 'unknown')}")
        print(f"  Chunk: {meta.get('chunk', 'unknown')}")
        print(f"  Text: {meta.get('text', '')[:100]}...")
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Print FAISS metadata")
    parser.add_argument("--lane", choices=["fast", "accurate"], required=True,
                       help="Lane to examine")
    parser.add_argument("--grep", type=str,
                       help="Filter by text content")
    parser.add_argument("--limit", type=int, default=10,
                       help="Maximum number of results to show")
    
    args = parser.parse_args()
    
    # Load metadata
    metadata = load_metadata(args.lane)
    
    # Print metadata
    print_metadata(metadata, args.grep, args.limit)


if __name__ == "__main__":
    main()
