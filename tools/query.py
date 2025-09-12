#!/usr/bin/env python3
"""
Interactive RAG Query Tool

A command-line interface for testing RAG retrieval across different lanes.
Allows you to query the fast (384d MiniLM) or accurate (768d MPNet + cross-encoder) lanes
without opening a Python REPL.

Usage:
    python3 tools/query.py "What is the Rhythm of Legacy?" --lane accurate --topk 3
    python3 tools/query.py "How do I handle rapid change?" --lane fast --topk 5
    python3 tools/query.py "Presence is productivity"  # defaults to fast lane, topk 5

Note: Run 'chmod +x tools/query.py' to make this script executable.
"""

import argparse
import os
import sys
import logging
from pathlib import Path

# Add lichen-protocol-mvp to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "lichen-protocol-mvp"))

# Set up RAG environment
os.environ["RAG_ENABLED"] = "1"

# Set up environment variables for per-lane indexes
os.environ["VECTOR_PATH_FAST"] = "lichen-protocol-mvp/.vector/fast.index.faiss"
os.environ["VECTOR_META_FAST"] = "lichen-protocol-mvp/.vector/fast.meta.jsonl"
os.environ["VECTOR_STATS_FAST"] = "lichen-protocol-mvp/.vector/fast.stats.json"
os.environ["VECTOR_PATH_ACCURATE"] = "lichen-protocol-mvp/.vector/accurate.index.faiss"
os.environ["VECTOR_META_ACCURATE"] = "lichen-protocol-mvp/.vector/accurate.meta.jsonl"
os.environ["VECTOR_STATS_ACCURATE"] = "lichen-protocol-mvp/.vector/accurate.stats.json"

# Suppress verbose logging
logging.getLogger().setLevel(logging.WARNING)

def run_query(adapter, query, lane, topk):
    """Run a single query and display results."""
    print(f"🔎 Query: {query}")
    print(f"📊 Lane: {lane.upper()}")
    print(f"🎯 Top-{topk} results:")
    print()
    
    results = adapter.retrieve(query, lane=lane)
    
    if not results:
        print("❌ No results found.")
        print("💡 Try a different query or check if the index is built.")
        return False
    
    # Display results
    for i, result in enumerate(results[:topk], 1):
        doc = result.get("doc", "unknown")
        chunk = result.get("chunk", 0)
        score = result.get("score", 0.0)
        text_preview = result.get("text", "")[:80] + "..." if len(result.get("text", "")) > 80 else result.get("text", "")
        
        print(f"  {i}. 📄 {doc} (chunk {chunk}) → score {score:.3f}")
        print(f"     💬 {text_preview}")
        print()
    
    # Show summary
    total_results = len(results)
    if total_results > topk:
        print(f"📈 Showing top {topk} of {total_results} total results")
    else:
        print(f"📈 Found {total_results} result{'s' if total_results != 1 else ''}")
    
    return True

def interactive_mode(default_lane="fast", default_topk=5):
    """Interactive mode for multiple queries."""
    try:
        # Import RAG adapter
        from hallway.adapters.rag_adapter import get_rag_adapter
        
        # Get RAG adapter instance
        print("🔧 Initializing RAG adapter...")
        adapter = get_rag_adapter()
        
        # Current settings
        current_lane = default_lane
        current_topk = default_topk
        
        print("🚀 Interactive RAG Query Tool")
        print("=" * 50)
        print(f"Current settings: Lane={current_lane.upper()}, TopK={current_topk}")
        print()
        print("Commands:")
        print("  /lane fast|accurate  - Switch lane")
        print("  /topk <number>       - Change number of results")
        print("  /help                - Show this help")
        print("  /quit, /exit, /q     - Exit")
        print("  <query>              - Search for query")
        print()
        
        while True:
            try:
                # Get user input
                user_input = input(f"🔍 [{current_lane.upper()}]> ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    cmd = user_input[1:].lower().split()
                    
                    if cmd[0] in ['quit', 'exit', 'q']:
                        print("👋 Goodbye!")
                        break
                    elif cmd[0] == 'help':
                        print("Commands:")
                        print("  /lane fast|accurate  - Switch lane")
                        print("  /topk <number>       - Change number of results")
                        print("  /help                - Show this help")
                        print("  /quit, /exit, /q     - Exit")
                        print("  <query>              - Search for query")
                        print()
                    elif cmd[0] == 'lane' and len(cmd) > 1:
                        new_lane = cmd[1].lower()
                        if new_lane in ['fast', 'accurate']:
                            current_lane = new_lane
                            print(f"✅ Switched to {current_lane.upper()} lane")
                        else:
                            print("❌ Invalid lane. Use 'fast' or 'accurate'")
                    elif cmd[0] == 'topk' and len(cmd) > 1:
                        try:
                            new_topk = int(cmd[1])
                            if new_topk > 0:
                                current_topk = new_topk
                                print(f"✅ TopK set to {current_topk}")
                            else:
                                print("❌ TopK must be a positive number")
                        except ValueError:
                            print("❌ TopK must be a number")
                    else:
                        print("❌ Unknown command. Type /help for available commands.")
                    continue
                
                # Run query
                print()
                success = run_query(adapter, user_input, current_lane, current_topk)
                print()
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break
        
        return 0
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running from the repository root and dependencies are installed.")
        return 1
        
    except FileNotFoundError as e:
        print(f"❌ Index not found: {e}")
        print(f"💡 The {default_lane} lane index may not be built yet.")
        print(f"💡 Run: python3 lichen-protocol-mvp/scripts/index_canon.py --lane {default_lane} --rebuild")
        return 1
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("💡 Check that the RAG system is properly configured.")
        return 1

def main():
    """Main function for the RAG query CLI."""
    parser = argparse.ArgumentParser(
        description="Interactive RAG Query Tool - Test retrieval across fast/accurate lanes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "What is the Rhythm of Legacy?" --lane accurate --topk 3
  %(prog)s "How do I handle rapid change?" --lane fast --topk 5
  %(prog)s "Presence is productivity"  # defaults to fast lane, topk 5
  %(prog)s --interactive  # Enter interactive mode for multiple queries
        """
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        help="The query string to search for (optional if using --interactive)"
    )
    
    parser.add_argument(
        "--lane",
        choices=["fast", "accurate"],
        default="fast",
        help="RAG lane to use (default: fast)"
    )
    
    parser.add_argument(
        "--topk",
        type=int,
        default=5,
        help="Number of top results to show (default: 5)"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enter interactive mode for multiple queries"
    )
    
    args = parser.parse_args()
    
    # If interactive mode or no query provided, enter interactive loop
    if args.interactive or not args.query:
        return interactive_mode(args.lane, args.topk)
    
    try:
        # Import RAG adapter
        from hallway.adapters.rag_adapter import get_rag_adapter
        
        # Get RAG adapter instance
        print(f"🔧 Initializing {args.lane} lane RAG adapter...")
        adapter = get_rag_adapter()
        
        # Run single query
        success = run_query(adapter, args.query, args.lane, args.topk)
        return 0 if success else 1
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running from the repository root and dependencies are installed.")
        return 1
        
    except FileNotFoundError as e:
        print(f"❌ Index not found: {e}")
        print(f"💡 The {args.lane} lane index may not be built yet.")
        print("💡 Run: python3 lichen-protocol-mvp/scripts/index_canon.py --lane {args.lane} --rebuild")
        return 1
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("💡 Check that the RAG system is properly configured.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
