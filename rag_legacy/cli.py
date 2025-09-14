"""
CLI commands for Protocol Router.

Provides commands for building protocol catalogs and testing routing.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, Any

from .router import build_protocol_catalog, parse_query, route_query, ProtocolRouter


def build_catalog_command(args):
    """Build protocol catalog with embeddings."""
    print(f"Building protocol catalog with model: {args.model}")
    
    try:
        catalog = build_protocol_catalog(args.model)
        print(f"Built catalog with {len(catalog)} protocols")
        
        # Print sample entries
        print("\nSample protocol entries:")
        for i, (protocol_id, entry) in enumerate(list(catalog.items())[:3]):
            print(f"\n{i+1}. {protocol_id}")
            print(f"   Title: {entry.title}")
            print(f"   Stones: {entry.stones}")
            print(f"   Key phrases: {entry.key_phrases[:3]}...")
        
        # Save catalog summary
        summary_file = Path(".vector/catalog_summary.json")
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        
        summary = {
            "model": args.model,
            "protocol_count": len(catalog),
            "protocols": [
                {
                    "protocol_id": entry.protocol_id,
                    "title": entry.title,
                    "stones": entry.stones,
                    "key_phrases_count": len(entry.key_phrases)
                }
                for entry in catalog.values()
            ]
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\nCatalog summary saved to {summary_file}")
        
    except Exception as e:
        print(f"Error building catalog: {e}")
        sys.exit(1)


def test_route_command(args):
    """Test routing for a query."""
    print(f"Testing routing for query: {args.query}")
    
    try:
        # Parse query
        parsed = parse_query(args.query)
        print(f"Parsed query:")
        print(f"  Normalized: {parsed.normalized_text}")
        print(f"  Stones signals: {parsed.stones_signals}")
        print(f"  Keywords: {parsed.keywords}")
        print(f"  Intents: {parsed.intents}")
        
        # Route query
        decision = route_query(parsed, k=args.k)
        print(f"\nRoute decision:")
        print(f"  Route: {decision.route}")
        print(f"  Confidence: {decision.confidence:.3f}")
        print(f"  Candidates:")
        
        for i, candidate in enumerate(decision.candidates, 1):
            print(f"    {i}. {candidate['protocol_id']} - {candidate['title']} (score: {candidate['score']:.3f})")
        
        # Save test result
        if args.output:
            result = {
                "query": args.query,
                "parsed": {
                    "normalized_text": parsed.normalized_text,
                    "stones_signals": parsed.stones_signals,
                    "keywords": parsed.keywords,
                    "intents": parsed.intents
                },
                "decision": {
                    "route": decision.route,
                    "confidence": decision.confidence,
                    "candidates": decision.candidates
                }
            }
            
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"\nTest result saved to {args.output}")
        
    except Exception as e:
        print(f"Error testing routing: {e}")
        sys.exit(1)


def batch_test_command(args):
    """Test routing for multiple queries from a file."""
    print(f"Batch testing routing from file: {args.input}")
    
    try:
        # Load test queries
        with open(args.input, 'r') as f:
            if args.input.endswith('.json'):
                test_data = json.load(f)
                queries = test_data.get("queries", [])
            else:
                # Assume one query per line
                queries = [line.strip() for line in f if line.strip()]
        
        print(f"Loaded {len(queries)} test queries")
        
        results = []
        for i, query in enumerate(queries, 1):
            print(f"\nTesting query {i}/{len(queries)}: {query}")
            
            try:
                parsed = parse_query(query)
                decision = route_query(parsed, k=args.k)
                
                result = {
                    "query": query,
                    "parsed": {
                        "normalized_text": parsed.normalized_text,
                        "stones_signals": parsed.stones_signals,
                        "keywords": parsed.keywords,
                        "intents": parsed.intents
                    },
                    "decision": {
                        "route": decision.route,
                        "confidence": decision.confidence,
                        "candidates": decision.candidates
                    }
                }
                
                results.append(result)
                
                print(f"  Route: {decision.route}, Confidence: {decision.confidence:.3f}")
                if decision.candidates:
                    print(f"  Top candidate: {decision.candidates[0]['protocol_id']}")
                
            except Exception as e:
                print(f"  Error: {e}")
                results.append({
                    "query": query,
                    "error": str(e)
                })
        
        # Save results
        output_file = args.output or "batch_test_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                "test_config": {
                    "k": args.k,
                    "input_file": args.input
                },
                "results": results
            }, f, indent=2)
        
        print(f"\nBatch test results saved to {output_file}")
        
        # Print summary
        successful = len([r for r in results if "error" not in r])
        print(f"Summary: {successful}/{len(queries)} queries processed successfully")
        
    except Exception as e:
        print(f"Error in batch testing: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Protocol Router CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Build catalog command
    build_parser = subparsers.add_parser("build-catalog", help="Build protocol catalog with embeddings")
    build_parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2", 
                             help="Embedding model to use")
    build_parser.set_defaults(func=build_catalog_command)
    
    # Test route command
    test_parser = subparsers.add_parser("test-route", help="Test routing for a single query")
    test_parser.add_argument("--query", required=True, help="Query to test")
    test_parser.add_argument("--k", type=int, default=3, help="Number of candidates to consider")
    test_parser.add_argument("--output", help="Output file for test result")
    test_parser.set_defaults(func=test_route_command)
    
    # Batch test command
    batch_parser = subparsers.add_parser("batch-test", help="Test routing for multiple queries")
    batch_parser.add_argument("--input", required=True, help="Input file with queries (JSON or text)")
    batch_parser.add_argument("--k", type=int, default=3, help="Number of candidates to consider")
    batch_parser.add_argument("--output", help="Output file for results")
    batch_parser.set_defaults(func=batch_test_command)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
