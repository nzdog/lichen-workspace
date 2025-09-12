#!/usr/bin/env python3
"""
Canon Reindex Pipeline

Handles automatic reindexing of protocol canon when files change.
Provides stats diffing, JSONL logging, and atomic index replacement.
"""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import yaml


# Configuration constants
CANON_PATH = Path("~/Desktop/Hybrid_SIS_Build/02_Canon_Exemplars/Protocol_Canon").expanduser()
SCHEMA_PATH = Path("lichen-chunker/libs/protocol_template_schema_v1.json")
SPEED_INDEX_DIR = Path("lichen-chunker/index/speed")
ACCURACY_INDEX_DIR = Path("lichen-chunker/index/accuracy")
REINDEX_LOG_DIR = Path("lichen-protocol-mvp/logs/rag/reindex")

# The 10 Stones for coverage analysis
STONES_LIST = [
    "light-before-form",
    "speed-of-trust", 
    "field-before-stones",
    "essence-first",
    "truth-over-comfort",
    "energy-follows-attention",
    "dynamics-over-content",
    "evolutionary-edge",
    "aligned-action",
    "presence-over-perfection"
]


class ReindexStats:
    """Statistics for reindex operations."""
    
    def __init__(self):
        self.protocols_count = 0
        self.total_tokens = 0
        self.avg_chunk_size = 0.0
        self.overlap_stats = {}
        self.stones_coverage = set()
        self.fields_coverage = set()
        self.manifest_data = {}
    
    @classmethod
    def from_manifest_file(cls, manifest_path: Path) -> 'ReindexStats':
        """Load stats from a manifest/stats file."""
        stats = cls()
        
        if not manifest_path.exists():
            return stats
            
        try:
            with open(manifest_path) as f:
                data = json.load(f)
                
            stats.protocols_count = data.get("protocols", 0)
            stats.total_tokens = data.get("total_tokens", 0)
            stats.avg_chunk_size = data.get("avg_chunk_size", 0.0)
            stats.overlap_stats = data.get("overlap_stats", {})
            stats.stones_coverage = set(data.get("stones_coverage", []))
            stats.fields_coverage = set(data.get("fields_coverage", []))
            stats.manifest_data = data
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not parse manifest {manifest_path}: {e}")
            
        return stats
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary for JSON serialization."""
        return {
            "protocols": self.protocols_count,
            "total_tokens": self.total_tokens,
            "avg_chunk_size": self.avg_chunk_size,
            "overlap_stats": self.overlap_stats,
            "stones_coverage": sorted(list(self.stones_coverage)),
            "fields_coverage": sorted(list(self.fields_coverage))
        }


class ReindexPipeline:
    """Main reindex pipeline implementation."""
    
    def __init__(self):
        self.canon_path = CANON_PATH
        self.schema_path = SCHEMA_PATH
        self.speed_index_dir = SPEED_INDEX_DIR
        self.accuracy_index_dir = ACCURACY_INDEX_DIR
        self.reindex_log_dir = REINDEX_LOG_DIR
        
        # Ensure log directory exists
        self.reindex_log_dir.mkdir(parents=True, exist_ok=True)
    
    def find_changed_files(self, since_minutes: Optional[int] = None) -> List[Path]:
        """
        Find JSON files in canon that have changed.
        
        Args:
            since_minutes: Only consider files changed in last N minutes
            
        Returns:
            List of changed file paths
        """
        if not self.canon_path.exists():
            print(f"Warning: Canon path does not exist: {self.canon_path}")
            return []
        
        changed_files = []
        cutoff_time = None
        
        if since_minutes is not None:
            cutoff_time = time.time() - (since_minutes * 60)
        
        # Find all JSON files in canon directory
        for json_file in self.canon_path.glob("*.json"):
            if cutoff_time is None or json_file.stat().st_mtime > cutoff_time:
                changed_files.append(json_file)
        
        return sorted(changed_files)
    
    def get_git_changed_files(self) -> List[Path]:
        """
        Get changed files using git diff.
        
        Returns:
            List of changed canon files from git diff
        """
        try:
            # Get changed files in canon directory
            cmd = ["git", "diff", "--name-only", "HEAD~1", "HEAD"]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.canon_path.parent)
            
            if result.returncode != 0:
                print(f"Git diff failed: {result.stderr}")
                return []
            
            changed_files = []
            for line in result.stdout.strip().split('\n'):
                if line and line.endswith('.json'):
                    file_path = self.canon_path.parent / line
                    if file_path.exists() and file_path.parent == self.canon_path:
                        changed_files.append(file_path)
            
            return changed_files
            
        except subprocess.SubprocessError as e:
            print(f"Error running git diff: {e}")
            return []
    
    def run_chunker_cli(self, profile: str) -> bool:
        """
        Run the lichen_chunker CLI for the specified profile.
        
        Args:
            profile: Either "speed" or "accuracy"
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = [
                "python", "-m", "lichen_chunker.cli", "process",
                "--profile", profile,
                "--schema", str(self.schema_path)
            ]
            
            print(f"Running chunker CLI for {profile} profile...")
            print(f"Command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ {profile} profile chunker completed successfully")
                return True
            else:
                print(f"❌ {profile} profile chunker failed:")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
                
        except subprocess.SubprocessError as e:
            print(f"Error running chunker CLI for {profile}: {e}")
            return False
    
    def move_indexes_atomically(self) -> bool:
        """
        Move newly generated indexes to their final locations atomically.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            for profile, target_dir in [("speed", self.speed_index_dir), ("accuracy", self.accuracy_index_dir)]:
                # Assume chunker CLI generates indexes in a temp location like "lichen-chunker/temp/{profile}/"
                temp_dir = Path(f"lichen-chunker/temp/{profile}")
                
                if not temp_dir.exists():
                    print(f"Warning: Expected temp directory not found: {temp_dir}")
                    continue
                
                # Create target directory
                target_dir.mkdir(parents=True, exist_ok=True)
                
                # Create atomic backup of existing index
                backup_dir = target_dir.parent / f"{target_dir.name}.backup"
                if target_dir.exists() and any(target_dir.iterdir()):
                    if backup_dir.exists():
                        shutil.rmtree(backup_dir)
                    shutil.move(str(target_dir), str(backup_dir))
                    target_dir.mkdir(parents=True, exist_ok=True)
                
                # Move new index into place
                for item in temp_dir.iterdir():
                    shutil.move(str(item), str(target_dir / item.name))
                
                # Clean up temp directory
                shutil.rmtree(temp_dir)
                
                # Remove backup on success
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)
                
                print(f"✅ Atomically moved {profile} index to {target_dir}")
            
            return True
            
        except Exception as e:
            print(f"Error moving indexes atomically: {e}")
            return False
    
    def collect_stats_from_manifest(self, index_dir: Path) -> ReindexStats:
        """
        Collect statistics from index manifest files.
        
        Args:
            index_dir: Directory containing index files
            
        Returns:
            ReindexStats object with collected data
        """
        stats = ReindexStats()
        
        # Look for manifest or stats files
        manifest_files = list(index_dir.glob("*.json")) + list(index_dir.glob("manifest.json"))
        
        for manifest_file in manifest_files:
            try:
                with open(manifest_file) as f:
                    data = json.load(f)
                
                # Extract protocol count
                if "protocols" in data:
                    stats.protocols_count = data["protocols"]
                elif isinstance(data, list):
                    stats.protocols_count = len(data)
                
                # Extract token information
                if "total_tokens" in data:
                    stats.total_tokens = data["total_tokens"]
                
                if "avg_chunk_size" in data:
                    stats.avg_chunk_size = data["avg_chunk_size"]
                
                # Extract stones coverage
                if "stones_coverage" in data:
                    stats.stones_coverage = set(data["stones_coverage"])
                elif "stones" in data:
                    if isinstance(data["stones"], list):
                        stats.stones_coverage = set(data["stones"])
                
                # Extract field coverage
                if "fields_coverage" in data:
                    stats.fields_coverage = set(data["fields_coverage"])
                
                stats.manifest_data = data
                break  # Use first valid manifest file
                
            except (json.JSONDecodeError, KeyError) as e:
                continue
        
        return stats
    
    def scan_canon_for_stats(self) -> ReindexStats:
        """
        Scan canon directory directly to generate stats.
        
        Returns:
            ReindexStats with current canon state
        """
        stats = ReindexStats()
        
        if not self.canon_path.exists():
            return stats
        
        protocols = list(self.canon_path.glob("*.json"))
        stats.protocols_count = len(protocols)
        
        total_words = 0
        protocol_count = 0
        
        for protocol_file in protocols:
            try:
                with open(protocol_file) as f:
                    protocol_data = json.load(f)
                
                protocol_count += 1
                
                # Count words in content
                content = protocol_data.get("content", "") or protocol_data.get("Content", "")
                if content:
                    total_words += len(content.split())
                
                # Extract stones
                stones = protocol_data.get("stones", [])
                if stones:
                    stats.stones_coverage.update(stones)
                
                # Extract field names
                stats.fields_coverage.update(protocol_data.keys())
                
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not parse {protocol_file}: {e}")
                continue
        
        # Calculate token estimates (rough approximation: 1 token ≈ 0.75 words)
        stats.total_tokens = int(total_words * 0.75)
        stats.avg_chunk_size = total_words / max(protocol_count, 1)
        
        return stats
    
    def compute_stats_diff(self, before_stats: ReindexStats, after_stats: ReindexStats) -> Dict[str, Any]:
        """
        Compute differences between before and after stats.
        
        Args:
            before_stats: Stats before reindex
            after_stats: Stats after reindex
            
        Returns:
            Dictionary with diff information
        """
        return {
            "protocols_before": before_stats.protocols_count,
            "protocols_after": after_stats.protocols_count,
            "stones_coverage_before": sorted(list(before_stats.stones_coverage)),
            "stones_coverage_after": sorted(list(after_stats.stones_coverage)),
            "fields_coverage_before": sorted(list(before_stats.fields_coverage)),
            "fields_coverage_after": sorted(list(after_stats.fields_coverage)),
            "tokens_added": after_stats.total_tokens - before_stats.total_tokens,
            "tokens_removed": max(0, before_stats.total_tokens - after_stats.total_tokens),
            "avg_chunk_size_before": before_stats.avg_chunk_size,
            "avg_chunk_size_after": after_stats.avg_chunk_size
        }
    
    def log_reindex_event(self, changed_files: List[Path], stats_diff: Dict[str, Any]) -> None:
        """
        Log reindex event to JSONL file.
        
        Args:
            changed_files: List of files that triggered the reindex
            stats_diff: Statistics diff from before/after reindex
        """
        # Generate log filename based on current date
        log_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self.reindex_log_dir / f"{log_date}.jsonl"
        
        # Create log entry
        log_entry = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "event": "reindex",
            "changed_files": [f.name for f in changed_files],
            "stats_diff": stats_diff
        }
        
        # Append to log file
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        print(f"📝 Logged reindex event to {log_file}")
    
    def reindex_once(self, changed_files: Optional[List[Path]] = None) -> bool:
        """
        Perform a one-shot reindex operation.
        
        Args:
            changed_files: Optional list of changed files (for logging)
            
        Returns:
            True if successful, False otherwise
        """
        print("🔄 Starting reindex operation...")
        
        # If no changed files provided, detect them
        if changed_files is None:
            changed_files = self.find_changed_files()
        
        # Collect before stats
        print("📊 Collecting before stats...")
        before_stats_speed = self.collect_stats_from_manifest(self.speed_index_dir)
        before_stats_accuracy = self.collect_stats_from_manifest(self.accuracy_index_dir)
        
        # If no existing stats, scan canon directly
        if before_stats_speed.protocols_count == 0:
            before_stats_speed = self.scan_canon_for_stats()
        if before_stats_accuracy.protocols_count == 0:
            before_stats_accuracy = self.scan_canon_for_stats()
        
        # Run chunker CLI for both profiles
        success_speed = self.run_chunker_cli("speed")
        success_accuracy = self.run_chunker_cli("accuracy")
        
        if not (success_speed and success_accuracy):
            print("❌ Chunker CLI failed, aborting reindex")
            return False
        
        # Move indexes atomically
        if not self.move_indexes_atomically():
            print("❌ Failed to move indexes atomically")
            return False
        
        # Collect after stats
        print("📊 Collecting after stats...")
        after_stats_speed = self.collect_stats_from_manifest(self.speed_index_dir)
        after_stats_accuracy = self.collect_stats_from_manifest(self.accuracy_index_dir)
        
        # If no manifest stats, scan canon again
        if after_stats_speed.protocols_count == 0:
            after_stats_speed = self.scan_canon_for_stats()
        if after_stats_accuracy.protocols_count == 0:
            after_stats_accuracy = self.scan_canon_for_stats()
        
        # Compute stats diff (use speed profile as primary)
        stats_diff = self.compute_stats_diff(before_stats_speed, after_stats_speed)
        
        # Log reindex event
        self.log_reindex_event(changed_files, stats_diff)
        
        print("✅ Reindex operation completed successfully")
        return True
    
    def print_stats_diff(self, stats_diff: Dict[str, Any]) -> None:
        """
        Print stats diff to stdout in human-readable format.
        
        Args:
            stats_diff: Stats diff dictionary
        """
        print("\n📊 Reindex Statistics Diff:")
        print("=" * 40)
        print(f"Protocols: {stats_diff['protocols_before']} → {stats_diff['protocols_after']}")
        
        tokens_change = stats_diff['tokens_added'] - stats_diff['tokens_removed']
        print(f"Tokens: {tokens_change:+,} ({stats_diff['tokens_added']:,} added, {stats_diff['tokens_removed']:,} removed)")
        
        print(f"Avg chunk size: {stats_diff['avg_chunk_size_before']:.1f} → {stats_diff['avg_chunk_size_after']:.1f}")
        
        stones_before = set(stats_diff['stones_coverage_before'])
        stones_after = set(stats_diff['stones_coverage_after'])
        stones_added = stones_after - stones_before
        stones_removed = stones_before - stones_after
        
        print(f"Stones coverage: {len(stones_before)} → {len(stones_after)}")
        if stones_added:
            print(f"  Added: {', '.join(sorted(stones_added))}")
        if stones_removed:
            print(f"  Removed: {', '.join(sorted(stones_removed))}")
        
        # Check coverage of all 10 stones
        missing_stones = set(STONES_LIST) - stones_after
        if missing_stones:
            print(f"  Missing from canon: {', '.join(sorted(missing_stones))}")
        else:
            print("  ✅ All 10 stones covered")
        
        fields_before = len(stats_diff['fields_coverage_before'])
        fields_after = len(stats_diff['fields_coverage_after'])
        print(f"Unique fields: {fields_before} → {fields_after}")
        print("=" * 40)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Canon Reindex Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --once                    # One-shot reindex
  %(prog)s --watch                   # Watch for changes (not implemented yet)
  %(prog)s --stats                   # Print last stats diff
        """
    )
    
    parser.add_argument(
        "--once",
        action="store_true", 
        default=True,
        help="One-shot reindex (default)"
    )
    
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch canon for changes and auto-reindex"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print stats diff to stdout"
    )
    
    parser.add_argument(
        "--since",
        type=int,
        help="Only consider files changed in last N minutes"
    )
    
    args = parser.parse_args()
    
    pipeline = ReindexPipeline()
    
    if args.stats:
        # Print last stats diff from log
        log_files = sorted(pipeline.reindex_log_dir.glob("*.jsonl"))
        if not log_files:
            print("No reindex log files found")
            return 1
        
        # Read last entry from most recent log file
        try:
            with open(log_files[-1]) as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1])
                    pipeline.print_stats_diff(last_entry["stats_diff"])
                else:
                    print("No reindex events found in log")
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Error reading stats from log: {e}")
            return 1
    
    elif args.watch:
        print("🔍 Watch mode not implemented yet")
        print("Use --once for one-shot reindex")
        return 1
    
    else:
        # One-shot mode
        changed_files = pipeline.find_changed_files(args.since)
        success = pipeline.reindex_once(changed_files)
        
        if args.stats and success:
            # Also print stats if requested
            log_files = sorted(pipeline.reindex_log_dir.glob("*.jsonl"))
            if log_files:
                try:
                    with open(log_files[-1]) as f:
                        lines = f.readlines()
                        if lines:
                            last_entry = json.loads(lines[-1])
                            pipeline.print_stats_diff(last_entry["stats_diff"])
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass
        
        return 0 if success else 1


if __name__ == "__main__":
    exit(main())