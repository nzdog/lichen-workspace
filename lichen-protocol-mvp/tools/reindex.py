#!/usr/bin/env python3
"""
Reindex CLI utility

Simple CLI interface for the Canon Reindex Pipeline.
"""

import argparse
import sys
from pathlib import Path

# Import the reindex pipeline
from reindex_pipeline import ReindexPipeline


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Canon Reindex CLI Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --once                    # One-shot reindex
  %(prog)s --watch                   # Watch for changes and auto-reindex  
  %(prog)s --stats                   # Print last stats diff to stdout
        """
    )
    
    # Mutually exclusive group for mode selection
    mode_group = parser.add_mutually_exclusive_group()
    
    mode_group.add_argument(
        "--once",
        action="store_true", 
        help="One-shot reindex (default)"
    )
    
    mode_group.add_argument(
        "--watch",
        action="store_true",
        help="Watch canon for changes and auto-reindex"
    )
    
    mode_group.add_argument(
        "--stats",
        action="store_true",
        help="Print last stats diff to stdout"
    )
    
    args = parser.parse_args()
    
    # Default to --once if no mode specified
    if not (args.once or args.watch or args.stats):
        args.once = True
    
    # Create pipeline instance
    pipeline = ReindexPipeline()
    
    if args.stats:
        # Print stats mode
        from reindex_pipeline import json
        
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
                    return 0
                else:
                    print("No reindex events found in log")
                    return 1
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Error reading stats from log: {e}")
            return 1
    
    elif args.watch:
        # Watch mode - use file watcher
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            import time
            
            class CanonFileHandler(FileSystemEventHandler):
                def __init__(self, pipeline):
                    self.pipeline = pipeline
                    self.last_reindex = 0
                    self.debounce_seconds = 5  # Debounce rapid changes
                
                def on_modified(self, event):
                    if event.is_directory:
                        return
                    
                    if not event.src_path.endswith('.json'):
                        return
                    
                    current_time = time.time()
                    if current_time - self.last_reindex < self.debounce_seconds:
                        return
                    
                    print(f"📁 Detected change: {event.src_path}")
                    changed_files = [Path(event.src_path)]
                    
                    success = self.pipeline.reindex_once(changed_files)
                    if success:
                        print("✅ Auto-reindex completed")
                    else:
                        print("❌ Auto-reindex failed")
                    
                    self.last_reindex = current_time
            
            # Set up file watcher
            event_handler = CanonFileHandler(pipeline)
            observer = Observer()
            observer.schedule(event_handler, str(pipeline.canon_path), recursive=False)
            observer.start()
            
            print(f"🔍 Watching {pipeline.canon_path} for changes...")
            print("Press Ctrl+C to stop")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
                print("\n🛑 Stopped watching")
            
            observer.join()
            return 0
            
        except ImportError:
            print("❌ watchdog package not installed. Install with: pip install watchdog")
            return 1
        except Exception as e:
            print(f"❌ Watch mode failed: {e}")
            return 1
    
    else:
        # One-shot mode
        print("🔄 Running one-shot reindex...")
        changed_files = pipeline.find_changed_files()
        
        if changed_files:
            print(f"📁 Found {len(changed_files)} changed files:")
            for f in changed_files:
                print(f"  - {f.name}")
        else:
            print("📁 No changed files found, reindexing all")
        
        success = pipeline.reindex_once(changed_files)
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())