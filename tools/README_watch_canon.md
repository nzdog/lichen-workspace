# Protocol Canon File Watcher

The `watch_canon.py` tool monitors the Protocol Canon directory for file changes and automatically triggers reindexing when files are modified, added, or deleted.

## Features

- **File Monitoring**: Watches `~/Desktop/Hybrid_SIS_Build/02_Canon_Exemplars/Protocol_Canon/` for changes
- **Automatic Reindexing**: Triggers re-chunking, re-embedding, and index rebuilding
- **Profile Support**: Handles both "speed" and "accuracy" profiles
- **Atomic Operations**: Ensures indexes are swapped atomically
- **Statistics Logging**: Logs detailed reindex statistics to JSONL files
- **Debouncing**: Prevents multiple triggers for the same file change

## Usage

### Basic Usage

```bash
# Start the watcher
python3 tools/watch_canon.py
```

### Advanced Usage

```bash
# Custom directories and settings
python3 tools/watch_canon.py \
  --canon-dir /path/to/canon \
  --chunker-dir /path/to/lichen-chunker \
  --index-dir /path/to/indexes \
  --log-dir /path/to/logs \
  --profiles speed accuracy \
  --debounce 2.0
```

### Command Line Options

- `--canon-dir`: Protocol Canon directory to watch (default: `~/Desktop/Hybrid_SIS_Build/02_Canon_Exemplars/Protocol_Canon`)
- `--chunker-dir`: Lichen chunker directory (default: `../lichen-chunker`)
- `--index-dir`: Index directory (default: `../lichen-chunker/index`)
- `--log-dir`: Log directory for reindex stats (default: `../lichen-protocol-mvp/logs/rag/reindex`)
- `--profiles`: Profiles to reindex (default: `speed accuracy`)
- `--debounce`: Debounce delay in seconds (default: `2.0`)

## How It Works

### 1. File Change Detection

The watcher monitors the Protocol Canon directory using the `watchdog` library and detects:
- File modifications
- File creations
- File deletions

### 2. Reindexing Process

When changes are detected, the watcher:

1. **Re-chunks** files using `lichen-chunker` CLI with the specified profile
2. **Re-embeds** chunks and rebuilds FAISS indexes
3. **Atomically swaps** indexes to ensure consistency
4. **Logs statistics** about the reindex operation

### 3. Statistics Logging

Each reindex operation is logged to `logs/rag/reindex/reindex_YYYY-MM-DD.jsonl` with:

```json
{
  "timestamp": "2025-09-12T05:30:00Z",
  "operation": "incremental",
  "files_changed": ["file1.json", "file2.json"],
  "files_added": ["new_file.json"],
  "files_removed": ["deleted_file.json"],
  "chunks_before": 1000,
  "chunks_after": 1200,
  "tokens_before": 50000,
  "tokens_after": 60000,
  "index_build_time_ms": 1500,
  "total_time_ms": 2000,
  "profile": "speed",
  "success": true,
  "error": null
}
```

## Dependencies

- `watchdog`: File system monitoring
- `lichen-chunker`: Chunking and embedding pipeline
- Python 3.7+

Install dependencies:

```bash
pip3 install watchdog
```

## Integration

The watcher integrates with:

- **Lichen Chunker**: Uses the CLI for chunking and embedding
- **RAG Pipeline**: Updates indexes used by the RAG service
- **Observability**: Logs detailed statistics for monitoring

## Monitoring

### View Logs

```bash
# Watch live logs
tail -f lichen-protocol-mvp/logs/rag/reindex/reindex_$(date +%Y-%m-%d).jsonl

# View all logs
ls -la lichen-protocol-mvp/logs/rag/reindex/
```

### Check Indexes

```bash
# Check speed profile index
ls -la lichen-chunker/index/speed/

# Check accuracy profile index
ls -la lichen-chunker/index/accuracy/
```

## Testing

To test the watcher:

1. Start the watcher in one terminal:
   ```bash
   python3 tools/watch_canon.py
   ```

2. In another terminal, touch a file:
   ```bash
   touch ~/Desktop/Hybrid_SIS_Build/02_Canon_Exemplars/Protocol_Canon/your_file.json
   ```

3. Watch the logs to see the reindex operation:
   ```bash
   tail -f lichen-protocol-mvp/logs/rag/reindex/reindex_$(date +%Y-%m-%d).jsonl
   ```

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure `watchdog` is installed
2. **Directory Not Found**: Verify the canon directory path
3. **Permission Denied**: Check file permissions for the canon directory
4. **Chunking Failed**: Ensure `lichen-chunker` is properly installed

### Debug Mode

For debugging, you can modify the script to add more verbose logging or run with Python's debugger.

## Acceptance Criteria

✅ **Touching a canon file triggers reindex**: File changes are detected and processed  
✅ **Stats diff is logged**: Detailed statistics are written to JSONL logs  
✅ **Token deltas tracked**: Before/after token counts are recorded  
✅ **Added/removed/changed files tracked**: File change types are logged  
✅ **Atomic index swapping**: Indexes are updated atomically  
✅ **Profile support**: Both speed and accuracy profiles are supported
