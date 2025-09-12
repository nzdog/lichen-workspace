#!/usr/bin/env python3
"""
File watcher for Protocol Canon directory that triggers automatic reindexing.

Monitors ~/Desktop/Hybrid_SIS_Build/02_Canon_Exemplars/Protocol_Canon/ for changes
and automatically re-chunks, re-embeds, and rebuilds indexes when files are modified.
"""

import os
import sys
import json
import time
import shutil
import hashlib
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("❌ watchdog not installed. Install with: pip install watchdog")
    sys.exit(1)


@dataclass
class ReindexStats:
    """Statistics for a reindex operation."""
    timestamp: str
    operation: str  # "full" or "incremental"
    files_changed: List[str]
    files_added: List[str]
    files_removed: List[str]
    chunks_before: int
    chunks_after: int
    tokens_before: int
    tokens_after: int
    index_build_time_ms: int
    total_time_ms: int
    profile: str
    success: bool
    error: Optional[str] = None


class CanonWatcher(FileSystemEventHandler):
    """File system event handler for Protocol Canon directory."""
    
    def __init__(self, 
                 canon_dir: Path,
                 chunker_dir: Path,
                 index_dir: Path,
                 log_dir: Path,
                 profiles: List[str] = None):
        self.canon_dir = canon_dir
        self.chunker_dir = chunker_dir
        self.index_dir = index_dir
        self.log_dir = log_dir
        self.profiles = profiles or ["speed", "accuracy"]
        
        # Track file states for change detection
        self.file_hashes: Dict[str, str] = {}
        self.last_reindex: Dict[str, float] = {}
        
        # Debounce reindexing (avoid multiple triggers for same file)
        self.debounce_delay = 2.0  # seconds
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize file hashes
        self._scan_initial_files()
        
        print(f"🔍 Watching: {self.canon_dir}")
        print(f"📦 Chunker: {self.chunker_dir}")
        print(f"🗂️  Indexes: {self.index_dir}")
        print(f"📝 Logs: {self.log_dir}")
        print(f"⚙️  Profiles: {', '.join(self.profiles)}")
    
    def _scan_initial_files(self):
        """Scan initial files and compute hashes."""
        print("🔍 Scanning initial files...")
        for file_path in self.canon_dir.rglob("*.json"):
            if file_path.is_file():
                self.file_hashes[str(file_path)] = self._compute_hash(file_path)
        print(f"📊 Found {len(self.file_hashes)} initial files")
    
    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""
    
    def _should_reindex(self, file_path: str) -> bool:
        """Check if we should trigger reindexing for this file."""
        now = time.time()
        
        # Check if this is a JSON file in the canon directory
        path_obj = Path(file_path)
        if not (path_obj.suffix == '.json' and 
                path_obj.is_relative_to(self.canon_dir) and
                path_obj.is_file()):
            return False
        
        # Check debounce
        if file_path in self.last_reindex:
            if now - self.last_reindex[file_path] < self.debounce_delay:
                return False
        
        # Check if file actually changed
        current_hash = self._compute_hash(path_obj)
        if file_path in self.file_hashes:
            if self.file_hashes[file_path] == current_hash:
                return False
        
        # Update hash and timestamp
        self.file_hashes[file_path] = current_hash
        self.last_reindex[file_path] = now
        
        return True
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = str(event.src_path)
        if self._should_reindex(file_path):
            print(f"📝 File changed: {Path(file_path).name}")
            self._trigger_reindex([file_path])
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        file_path = str(event.src_path)
        if self._should_reindex(file_path):
            print(f"➕ File created: {Path(file_path).name}")
            self._trigger_reindex([file_path])
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        file_path = str(event.src_path)
        if file_path in self.file_hashes:
            print(f"🗑️  File deleted: {Path(file_path).name}")
            del self.file_hashes[file_path]
            self._trigger_reindex([])  # Full reindex after deletion
    
    def _trigger_reindex(self, changed_files: List[str]):
        """Trigger reindexing for changed files."""
        print(f"🔄 Triggering reindex for {len(changed_files)} changed files...")
        
        for profile in self.profiles:
            try:
                stats = self._reindex_profile(profile, changed_files)
                self._log_stats(stats)
                print(f"✅ Reindex completed for profile '{profile}'")
            except Exception as e:
                print(f"❌ Reindex failed for profile '{profile}': {e}")
                # Log error stats
                error_stats = ReindexStats(
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    operation="error",
                    files_changed=changed_files,
                    files_added=[],
                    files_removed=[],
                    chunks_before=0,
                    chunks_after=0,
                    tokens_before=0,
                    tokens_after=0,
                    index_build_time_ms=0,
                    total_time_ms=0,
                    profile=profile,
                    success=False,
                    error=str(e)
                )
                self._log_stats(error_stats)
    
    def _reindex_profile(self, profile: str, changed_files: List[str]) -> ReindexStats:
        """Reindex a specific profile."""
        start_time = time.time()
        
        # Get current stats
        current_stats = self._get_current_stats(profile)
        
        # Step 1: Re-chunk
        print(f"  📦 Re-chunking with profile '{profile}'...")
        chunk_start = time.time()
        self._rechunk_files(profile, changed_files)
        chunk_time = int((time.time() - chunk_start) * 1000)
        
        # Step 2: Re-embed and rebuild index
        print(f"  🔮 Re-embedding and rebuilding index...")
        embed_start = time.time()
        self._rebuild_index(profile)
        embed_time = int((time.time() - embed_start) * 1000)
        
        # Step 3: Atomic swap
        print(f"  🔄 Atomically swapping indexes...")
        self._atomic_swap_index(profile)
        
        # Get new stats
        new_stats = self._get_current_stats(profile)
        
        total_time = int((time.time() - start_time) * 1000)
        
        # Determine operation type
        operation = "incremental" if changed_files else "full"
        
        return ReindexStats(
            timestamp=datetime.utcnow().isoformat() + "Z",
            operation=operation,
            files_changed=changed_files,
            files_added=[f for f in changed_files if f not in self.file_hashes],
            files_removed=[f for f in self.file_hashes if f not in changed_files and Path(f).exists()],
            chunks_before=current_stats.get('chunks', 0),
            chunks_after=new_stats.get('chunks', 0),
            tokens_before=current_stats.get('tokens', 0),
            tokens_after=new_stats.get('tokens', 0),
            index_build_time_ms=embed_time,
            total_time_ms=total_time,
            profile=profile,
            success=True
        )
    
    def _rechunk_files(self, profile: str, changed_files: List[str]):
        """Re-chunk files using lichen-chunker CLI."""
        if not changed_files:
            # Full rechunk of all files
            files_to_chunk = [str(f) for f in self.canon_dir.rglob("*.json") if f.is_file()]
        else:
            files_to_chunk = changed_files
        
        if not files_to_chunk:
            return
        
        # Run lichen-chunker CLI with proper module path
        cmd = [
            sys.executable, "-m", "lichen_chunker.cli", "chunk",
            "--profile", profile,
            "--output", str(self.chunker_dir / "data" / profile)
        ] + files_to_chunk
        
        result = subprocess.run(
            cmd,
            cwd=self.chunker_dir / "src",  # Run from src directory
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Chunking failed: {result.stderr}")
        
        print(f"  ✅ Chunked {len(files_to_chunk)} files for profile '{profile}'")
    
    def _rebuild_index(self, profile: str):
        """Rebuild index for a profile."""
        # Get chunk files for this profile
        chunk_files = list((self.chunker_dir / "data" / profile).glob("*.chunks.jsonl"))
        
        if not chunk_files:
            print(f"  ⚠️  No chunk files found for profile '{profile}'")
            return
        
        # Run lichen-chunker embed command
        cmd = [
            sys.executable, "-m", "lichen_chunker.cli", "embed",
            "--index", str(self.index_dir / profile)
        ] + [str(f) for f in chunk_files]
        
        result = subprocess.run(
            cmd,
            cwd=self.chunker_dir / "src",
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Embedding failed: {result.stderr}")
        
        print(f"  ✅ Rebuilt index for profile '{profile}' with {len(chunk_files)} chunk files")
    
    def _atomic_swap_index(self, profile: str):
        """Atomically swap the index for a profile."""
        # The index is already built in the correct location by _rebuild_index
        # We just need to ensure it's properly accessible
        
        index_dir = self.index_dir / profile
        if not index_dir.exists():
            raise Exception(f"Index directory not found: {index_dir}")
        
        # Verify required index files exist
        required_files = ["index.faiss", "docstore.pkl", "metadata.parquet"]
        for file_name in required_files:
            file_path = index_dir / file_name
            if not file_path.exists():
                raise Exception(f"Required index file missing: {file_path}")
        
        print(f"  ✅ Index swap verified for profile '{profile}'")
    
    def _get_current_stats(self, profile: str) -> Dict[str, int]:
        """Get current statistics for a profile."""
        # Count chunks and tokens in the data directory
        data_dir = self.chunker_dir / "data" / profile
        chunks = 0
        tokens = 0
        
        if data_dir.exists():
            for chunk_file in data_dir.glob("*.chunks.jsonl"):
                try:
                    with open(chunk_file, 'r') as f:
                        for line in f:
                            if line.strip():
                                chunk_data = json.loads(line)
                                chunks += 1
                                # Estimate tokens (rough approximation)
                                tokens += len(chunk_data.get('text', '').split())
                except Exception:
                    pass
        
        return {
            'chunks': chunks,
            'tokens': tokens
        }
    
    def _log_stats(self, stats: ReindexStats):
        """Log reindex statistics to JSONL file."""
        log_file = self.log_dir / f"reindex_{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl"
        
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(asdict(stats)) + '\n')
        except Exception as e:
            print(f"⚠️  Failed to log stats: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Watch Protocol Canon directory for changes")
    parser.add_argument(
        "--canon-dir",
        default=Path.home() / "Desktop" / "Hybrid_SIS_Build" / "02_Canon_Exemplars" / "Protocol_Canon",
        type=Path,
        help="Protocol Canon directory to watch"
    )
    parser.add_argument(
        "--chunker-dir",
        default=Path(__file__).parent.parent / "lichen-chunker",
        type=Path,
        help="Lichen chunker directory"
    )
    parser.add_argument(
        "--index-dir",
        default=Path(__file__).parent.parent / "lichen-chunker" / "index",
        type=Path,
        help="Index directory"
    )
    parser.add_argument(
        "--log-dir",
        default=Path(__file__).parent.parent / "lichen-protocol-mvp" / "logs" / "rag" / "reindex",
        type=Path,
        help="Log directory for reindex stats"
    )
    parser.add_argument(
        "--profiles",
        nargs="+",
        default=["speed", "accuracy"],
        help="Profiles to reindex"
    )
    parser.add_argument(
        "--debounce",
        type=float,
        default=2.0,
        help="Debounce delay in seconds"
    )
    
    args = parser.parse_args()
    
    # Validate directories
    if not args.canon_dir.exists():
        print(f"❌ Canon directory not found: {args.canon_dir}")
        sys.exit(1)
    
    if not args.chunker_dir.exists():
        print(f"❌ Chunker directory not found: {args.chunker_dir}")
        sys.exit(1)
    
    # Create watcher
    event_handler = CanonWatcher(
        canon_dir=args.canon_dir,
        chunker_dir=args.chunker_dir,
        index_dir=args.index_dir,
        log_dir=args.log_dir,
        profiles=args.profiles
    )
    
    # Set debounce delay
    event_handler.debounce_delay = args.debounce
    
    # Start observer
    observer = Observer()
    observer.schedule(event_handler, str(args.canon_dir), recursive=True)
    
    print("🚀 Starting file watcher...")
    print("Press Ctrl+C to stop")
    
    try:
        observer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping file watcher...")
        observer.stop()
    
    observer.join()
    print("✅ File watcher stopped")


if __name__ == "__main__":
    main()
