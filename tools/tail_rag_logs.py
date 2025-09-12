#!/usr/bin/env python3
"""
RAG logs tailer for real-time observability.

Usage examples:
    # Follow today's log, default view
    python3 tools/tail_rag_logs.py --follow

    # Filter only accurate lane  
    python3 tools/tail_rag_logs.py --follow --jq '. | select(.lane=="accurate")'

    # Show slow turns
    python3 tools/tail_rag_logs.py --jq '. | select(.retrieval.elapsed_ms>300)'

    # Specific date
    python3 tools/tail_rag_logs.py --file logs/rag/2025-09-11.jsonl

    # Just print last 10 lines
    python3 tools/tail_rag_logs.py --lines 10
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List


def get_today_log_file(obs_dir: str = "logs/rag") -> str:
    """Get today's log file path."""
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(obs_dir, f"{today}.jsonl")


def has_jq() -> bool:
    """Check if jq is available."""
    try:
        subprocess.run(["jq", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def apply_jq_filter(line: str, jq_filter: str) -> Optional[str]:
    """Apply jq filter to a JSON line."""
    try:
        cmd = ["jq", "-c", jq_filter]
        result = subprocess.run(cmd, input=line, text=True, capture_output=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except Exception:
        return None


def format_default_view(event: Dict[str, Any]) -> str:
    """Format event in default pretty view."""
    try:
        ts = event.get("ts", "")[:19].replace("T", " ")  # Remove Z and milliseconds
        lane = event.get("lane", "unknown")
        
        # Retrieval info
        retrieval = event.get("retrieval", {})
        retrieval_ms = retrieval.get("elapsed_ms", 0)
        topk = retrieval.get("topk", 0)
        embed_model = retrieval.get("embed_model", "unknown")
        
        # Generation info
        generation = event.get("generation", {})
        grounding = generation.get("grounding", 0)
        gen_ms = generation.get("elapsed_ms", 0)
        
        # Top 3 results
        results = event.get("results", [])[:3]
        result_docs = [r.get("doc", "")[:20] + "..." if len(r.get("doc", "")) > 20 else r.get("doc", "") 
                      for r in results]
        
        # Build output line
        parts = [
            f"{ts}",
            f"{lane:8}",
            f"ret:{retrieval_ms:6.1f}ms",
            f"gen:{gen_ms:6.1f}ms", 
            f"k={topk:2}",
            f"ground:{grounding:3.1f}",
            f"model:{embed_model.split('/')[-1][:15]:15}",
            f"docs:[{', '.join(result_docs[:2])}]"
        ]
        
        return " ".join(parts)
        
    except Exception as e:
        return f"Format error: {e}"


def tail_file(file_path: str, follow: bool = False, jq_filter: Optional[str] = None, 
              lines: Optional[int] = None) -> None:
    """Tail a RAG log file with optional filtering and formatting."""
    
    file_path = Path(file_path)
    
    if not file_path.exists():
        if follow:
            print(f"Waiting for {file_path} to be created...")
            while not file_path.exists():
                time.sleep(1)
        else:
            print(f"File not found: {file_path}")
            return
    
    # Print header for default view
    if not jq_filter:
        print("Time               Lane     Retrieval  Generation K  Ground Model           Documents")
        print("-" * 100)
    
    # Handle --lines option (like tail -n)
    if lines and not follow:
        try:
            with open(file_path, 'r') as f:
                all_lines = f.readlines()
                start_idx = max(0, len(all_lines) - lines)
                for line in all_lines[start_idx:]:
                    process_line(line.strip(), jq_filter)
        except Exception as e:
            print(f"Error reading file: {e}")
        return
    
    # Follow mode or read entire file
    try:
        with open(file_path, 'r') as f:
            # Read existing content
            if not follow:
                for line in f:
                    process_line(line.strip(), jq_filter)
                return
            
            # Follow mode: read existing then follow
            for line in f:
                process_line(line.strip(), jq_filter)
            
            # Follow new lines
            while follow:
                line = f.readline()
                if line:
                    process_line(line.strip(), jq_filter)
                else:
                    time.sleep(0.1)  # Small delay when no new data
                    
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")


def process_line(line: str, jq_filter: Optional[str] = None) -> None:
    """Process a single log line."""
    if not line:
        return
    
    try:
        if jq_filter:
            # Apply jq filter if available
            if has_jq():
                filtered = apply_jq_filter(line, jq_filter)
                if filtered:
                    print(filtered)
            else:
                print(f"jq not available, showing raw line: {line}")
        else:
            # Default formatted view
            event = json.loads(line)
            formatted = format_default_view(event)
            print(formatted)
            
    except json.JSONDecodeError:
        print(f"Invalid JSON: {line}")
    except Exception as e:
        print(f"Error processing line: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Tail RAG observability logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--file", "-f",
        help="Log file to tail (default: today's file in logs/rag/)"
    )
    
    parser.add_argument(
        "--follow", 
        action="store_true",
        default=True,
        help="Follow the file for new entries (default: true)"
    )
    
    parser.add_argument(
        "--no-follow",
        action="store_true", 
        help="Don't follow, just print existing content"
    )
    
    parser.add_argument(
        "--jq",
        help="jq filter expression (requires jq to be installed)"
    )
    
    parser.add_argument(
        "--lines", "-n",
        type=int,
        help="Show last N lines (like tail -n), implies --no-follow"
    )
    
    parser.add_argument(
        "--obs-dir",
        default="logs/rag",
        help="RAG observability directory (default: logs/rag)"
    )
    
    args = parser.parse_args()
    
    # Determine file to tail
    if args.file:
        log_file = args.file
    else:
        log_file = get_today_log_file(args.obs_dir)
    
    # Determine follow mode
    follow = args.follow and not args.no_follow and not args.lines
    
    print(f"Tailing: {log_file}")
    if follow:
        print("Press Ctrl+C to stop")
    print()
    
    tail_file(log_file, follow=follow, jq_filter=args.jq, lines=args.lines)


if __name__ == "__main__":
    main()
