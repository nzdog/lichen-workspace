#!/usr/bin/env python3
"""
RAG log tailing tool with filtering and rolling p95 computation.

Provides real-time monitoring of RAG operations with filters for lane, grounding score,
and latency thresholds. Computes rolling percentiles for performance monitoring.
"""

import argparse
import json
import time
import glob
import os
from datetime import datetime, timedelta, timezone
from collections import deque
from typing import List, Dict, Any, Optional
import sys


class RollingPercentiles:
    """Compute rolling percentiles efficiently using sorted deques."""
    
    def __init__(self, window_size: int = 200):
        self.window_size = window_size
        self.values = deque()
        self.sorted_values = []
        
    def add(self, value: float):
        """Add a new value to the rolling window."""
        if value is None:
            return
            
        self.values.append(value)
        
        # Maintain window size
        if len(self.values) > self.window_size:
            old_value = self.values.popleft()
            if old_value in self.sorted_values:
                self.sorted_values.remove(old_value)
        
        # Insert new value in sorted position
        import bisect
        bisect.insort(self.sorted_values, value)
    
    def percentile(self, p: float) -> Optional[float]:
        """Get the p-th percentile (0.0 to 1.0)."""
        if not self.sorted_values:
            return None
            
        n = len(self.sorted_values)
        if n == 1:
            return self.sorted_values[0]
            
        idx = p * (n - 1)
        if idx == int(idx):
            return self.sorted_values[int(idx)]
        else:
            # Linear interpolation
            lower_idx = int(idx)
            upper_idx = min(lower_idx + 1, n - 1)
            weight = idx - lower_idx
            return (1 - weight) * self.sorted_values[lower_idx] + weight * self.sorted_values[upper_idx]
    
    def p95(self) -> Optional[float]:
        """Get the 95th percentile."""
        return self.percentile(0.95)


class RAGLogTailer:
    """RAG log tailing and filtering tool."""
    
    def __init__(self, args):
        self.args = args
        self.log_dir = "logs/rag"
        self.event_count = 0
        
        # Performance budget targets (ms)
        self.budget_targets = {
            "fast": 150.0,
            "accurate": 500.0
        }
        
        # Rolling percentile trackers
        self.p95_total = RollingPercentiles(args.p95_window)
        self.p95_retrieve = RollingPercentiles(args.p95_window)
        self.p95_rerank = RollingPercentiles(args.p95_window)
        self.p95_synth = RollingPercentiles(args.p95_window)
        
        # Lane-specific percentile trackers for budget checking
        self.p95_by_lane = {
            "fast": RollingPercentiles(args.p95_window),
            "accurate": RollingPercentiles(args.p95_window)
        }
        
    def get_latest_log_file(self) -> Optional[str]:
        """Get the path to the latest log file."""
        pattern = os.path.join(self.log_dir, "*.jsonl")
        log_files = glob.glob(pattern)
        
        if not log_files:
            return None
            
        # Sort by modification time, return the newest
        log_files.sort(key=os.path.getmtime, reverse=True)
        return log_files[0]
    
    def parse_event(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a JSONL log line into an event dict."""
        try:
            return json.loads(line.strip())
        except json.JSONDecodeError:
            return None
    
    def matches_filters(self, event: Dict[str, Any]) -> bool:
        """Check if event matches all filters."""
        # Budget check mode has different filtering
        if self.args.budget_check:
            return self.matches_budget_filters(event)
            
        # Lane filter
        if self.args.lane != "any" and event.get("lane") != self.args.lane:
            return False
            
        # Grounding score filter
        if self.args.min_grounding is not None:
            grounding = event.get("grounding_score")
            if grounding is None or grounding < self.args.min_grounding:
                return False
        
        # Slow timing filter
        if self.args.slow_ms is not None:
            stages = event.get("stages", {})
            total_ms = stages.get("total_ms")
            if total_ms is None or total_ms < self.args.slow_ms:
                return False
                
        # Time window filter
        if self.args.since:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.args.since)
            event_ts = event.get("ts", "")
            try:
                event_time = datetime.fromisoformat(event_ts.rstrip('Z'))
                if event_time < cutoff:
                    return False
            except (ValueError, TypeError):
                pass
                
        return True
    
    def matches_budget_filters(self, event: Dict[str, Any]) -> bool:
        """Check if event should be included in budget analysis."""
        # Exclude warmup events
        flags = event.get("flags", {})
        if flags.get("warmup", False):
            return False
            
        # Only include events with valid timing data
        stages = event.get("stages", {})
        total_ms = stages.get("total_ms")
        if total_ms is None:
            return False
            
        # Only include fast and accurate lanes
        lane = event.get("lane", "")
        if lane not in ["fast", "accurate"]:
            return False
            
        # Apply time window filter if specified
        if self.args.since:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.args.since)
            event_ts = event.get("ts", "")
            try:
                event_time = datetime.fromisoformat(event_ts.rstrip('Z'))
                if event_time < cutoff:
                    return False
            except (ValueError, TypeError):
                pass
                
        return True
    
    def format_event(self, event: Dict[str, Any]) -> str:
        """Format an event for compact one-line display."""
        ts = event.get("ts", "")[:19].replace("T", " ")[11:]  # Just HH:MM:SS
        if not ts:
            ts = "??:??:??"
            
        request_id = event.get("request_id", "unknown")[:8]
        lane = event.get("lane", "?")
        topk = event.get("topk", 0)
        
        grounding = event.get("grounding_score")
        g_str = f"g={grounding:.2f}" if grounding is not None else "g=null"
        
        stages = event.get("stages", {})
        total_ms = stages.get("total_ms", 0)
        retrieve_ms = stages.get("retrieve_ms", 0)
        rerank_ms = stages.get("rerank_ms", 0)
        synth_ms = stages.get("synth_ms", 0)
        
        citations_count = len(event.get("citations", []))
        
        timing_str = f"ret={retrieve_ms} rer={rerank_ms} syn={synth_ms}"
        
        return (f"{ts}Z | req={request_id}... | lane={lane} k={topk} | {g_str} | "
                f"t={total_ms}ms ({timing_str}) | cites={citations_count}")
    
    def update_percentiles(self, event: Dict[str, Any]):
        """Update rolling percentiles with event timing data."""
        stages = event.get("stages", {})
        
        self.p95_total.add(stages.get("total_ms"))
        self.p95_retrieve.add(stages.get("retrieve_ms"))
        self.p95_rerank.add(stages.get("rerank_ms"))
        self.p95_synth.add(stages.get("synth_ms"))
        
        # Update lane-specific tracking for budget checks
        lane = event.get("lane", "")
        if lane in self.p95_by_lane:
            total_ms = stages.get("total_ms")
            if total_ms is not None:
                self.p95_by_lane[lane].add(total_ms)
    
    def print_p95_header(self):
        """Print rolling p95 statistics header."""
        total_p95 = self.p95_total.p95()
        retrieve_p95 = self.p95_retrieve.p95()
        rerank_p95 = self.p95_rerank.p95()
        synth_p95 = self.p95_synth.p95()
        
        def fmt_ms(val):
            return f"{val:.0f}ms" if val is not None else "null"
            
        if self.args.budget_check:
            self.print_budget_status()
        else:
            print(f"\\np95 (window={self.args.p95_window}): "
                  f"total={fmt_ms(total_p95)}  retrieve={fmt_ms(retrieve_p95)}  "
                  f"rerank={fmt_ms(rerank_p95)}  synth={fmt_ms(synth_p95)}\\n")
    
    def print_budget_status(self):
        """Print budget check status for each lane."""
        print("\\n" + "="*50)
        print("PERFORMANCE BUDGET CHECK")
        print("="*50)
        
        for lane, tracker in self.p95_by_lane.items():
            p95 = tracker.p95()
            target = self.budget_targets[lane]
            
            if p95 is None:
                status = "❓ (no data)"
                status_msg = f"Lane {lane:<8} p95=N/A      {status} (target {target:.0f}ms)"
            else:
                if p95 <= target:
                    status = "✅"
                    status_msg = f"Lane {lane:<8} p95={p95:.0f}ms  {status} (target {target:.0f}ms)"
                else:
                    status = "❌"
                    over_pct = ((p95 - target) / target) * 100
                    status_msg = f"Lane {lane:<8} p95={p95:.0f}ms  {status} (target {target:.0f}ms, +{over_pct:.1f}%)"
            
            print(status_msg)
        
        print("="*50)
        print(f"Window size: {self.args.p95_window} events (warmup excluded)")
        print("="*50 + "\\n")
    
    def process_events(self, events: List[str]):
        """Process a list of event lines."""
        for line in events:
            if not line.strip():
                continue
                
            event = self.parse_event(line)
            if not event:
                continue
                
            if not self.matches_filters(event):
                continue
                
            # Update percentiles
            self.update_percentiles(event)
            
            # Print event (skip in budget check mode to avoid spam)
            if not self.args.budget_check:
                print(self.format_event(event))
            
            self.event_count += 1
            
            # Print p95 header every 10 events
            if self.event_count % 10 == 0:
                self.print_p95_header()
    
    def tail_file(self, filepath: str):
        """Tail a log file, processing new events as they arrive."""
        print(f"Tailing {filepath} (--follow mode, Ctrl+C to stop)")
        
        try:
            with open(filepath, 'r') as f:
                # Process existing content if --since filter is active
                if self.args.since:
                    existing_lines = f.readlines()
                    self.process_events(existing_lines)
                else:
                    # Skip to end for follow mode
                    f.seek(0, 2)
                
                # Follow new content
                while True:
                    line = f.readline()
                    if line:
                        self.process_events([line])
                    else:
                        time.sleep(0.1)  # Brief pause before checking again
                        
        except KeyboardInterrupt:
            print("\\nStopped tailing.")
            return
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            return
    
    def read_file_once(self, filepath: str):
        """Read and process a log file once (non-follow mode)."""
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
                self.process_events(lines)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
    
    def run(self):
        """Main entry point."""
        log_file = self.get_latest_log_file()
        
        if not log_file:
            print("no logs yet")
            return 0
        
        if self.args.follow:
            self.tail_file(log_file)
        else:
            self.read_file_once(log_file)
            
            # Print final budget check status if in budget check mode
            if self.args.budget_check:
                self.print_budget_status()
                
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Tail RAG logs with filtering and p95 monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --follow --lane fast --min-grounding 0.5
  %(prog)s --since 30 --slow-ms 200
  %(prog)s --follow --p95-window 100
  %(prog)s --budget-check --p95-window 500
  %(prog)s --budget-check --follow
        """
    )
    
    parser.add_argument(
        "--follow", 
        action="store_true",
        help="Follow log file like tail -f"
    )
    
    parser.add_argument(
        "--since", 
        type=int, 
        default=60,
        help="Show events from last N minutes (default: 60)"
    )
    
    parser.add_argument(
        "--lane",
        choices=["fast", "accurate", "any"],
        default="any",
        help="Filter by RAG lane (default: any)"
    )
    
    parser.add_argument(
        "--min-grounding",
        type=float,
        help="Filter by minimum grounding score"
    )
    
    parser.add_argument(
        "--slow-ms",
        type=int,
        help="Filter by minimum total latency in milliseconds"
    )
    
    parser.add_argument(
        "--p95-window",
        type=int,
        default=200,
        help="Rolling window size for p95 computation (default: 200)"
    )
    
    parser.add_argument(
        "--budget-check",
        action="store_true",
        help="Check performance budgets (excludes warmup, shows pass/fail vs targets)"
    )
    
    args = parser.parse_args()
    
    tailer = RAGLogTailer(args)
    return tailer.run()


if __name__ == "__main__":
    sys.exit(main())