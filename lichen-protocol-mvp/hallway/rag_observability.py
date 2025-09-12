"""
RAG Observability logging system.

Provides JSONL logging for RAG operations with configurable sampling,
redaction, and file rotation. All logging is opt-in via environment flags.
"""

import os
import json
import time
import uuid
import hashlib
import socket
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from .redaction import get_redactor

logger = logging.getLogger(__name__)

# Global state for run_id (stable per process)
_run_id = str(uuid.uuid4())


class RAGObservability:
    """RAG observability logging system."""
    
    def __init__(self):
        """Initialize observability system."""
        self.enabled = os.getenv("RAG_OBS_ENABLED", "0") == "1"
        self.obs_dir = os.getenv("RAG_OBS_DIR", "logs/rag")
        self.obs_file = os.getenv("RAG_OBS_FILE", "")  # Empty means auto-rotate by day
        self.sampling_rate = float(os.getenv("RAG_OBS_SAMPLING", "1.0"))
        self.redact = os.getenv("RAG_OBS_REDACT", "0") == "1"
        self.max_len = int(os.getenv("RAG_OBS_MAXLEN", "2000"))
        self.include_context = os.getenv("RAG_OBS_INCLUDE_CONTEXT", "0") == "1"
        
        # Ensure log directory exists
        if self.enabled:
            Path(self.obs_dir).mkdir(parents=True, exist_ok=True)
    
    def _should_sample(self) -> bool:
        """Check if this event should be sampled."""
        if self.sampling_rate >= 1.0:
            return True
        if self.sampling_rate <= 0.0:
            return False
        import random
        return random.random() < self.sampling_rate
    
    def _get_log_file_path(self) -> str:
        """Get the log file path for today."""
        if self.obs_file:
            return os.path.join(self.obs_dir, self.obs_file)
        else:
            # Auto-rotate by day
            today = datetime.utcnow().strftime("%Y-%m-%d")
            return os.path.join(self.obs_dir, f"{today}.jsonl")
    
    def _truncate_text(self, text: str) -> str:
        """Truncate text to max_len if needed."""
        if len(text) <= self.max_len:
            return text
        return text[:self.max_len] + "..."
    
    def _redact_query(self, query: str) -> Dict[str, Any]:
        """Redact query text, returning hash and length."""
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        return {
            "hash": query_hash,
            "len": len(query)
        }
    
    def _get_meta_info(self) -> Dict[str, Any]:
        """Get metadata about the current process."""
        try:
            hostname = socket.gethostname()
        except:
            hostname = "unknown"
        
        try:
            pid = os.getpid()
        except:
            pid = 0
        
        # Try to get git version
        version = "unknown"
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
        except:
            pass
        
        return {
            "app": "ai_room",
            "host": hostname,
            "pid": pid,
            "version": version
        }
    
    def _extract_citations_from_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract citations array from retrieval results.
        
        Args:
            results: List of retrieval results
            
        Returns:
            List of citations with source_id, span_start, span_end
        """
        citations = []
        
        for result in results:
            # Extract source information
            source_id = result.get("doc_id", "")
            if not source_id:
                continue
            
            # Extract span information
            spans = result.get("spans", [])
            if spans:
                for span in spans:
                    citations.append({
                        "source_id": source_id,
                        "span_start": span.get("start", 0),
                        "span_end": span.get("end", 0)
                    })
            else:
                # If no spans, create a citation for the entire chunk
                citations.append({
                    "source_id": source_id,
                    "span_start": 0,
                    "span_end": len(result.get("text", ""))
                })
        
        return citations
    
    def log_rag_turn(self, 
                    request_id: str,
                    lane: str,
                    query: str,
                    topk: int,
                    stages: Dict[str, int],
                    grounding_score: Optional[float] = None,
                    stones: Optional[List[str]] = None,
                    citations: Optional[List[Dict[str, Any]]] = None,
                    flags: Optional[Dict[str, Any]] = None,
                    trace: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a RAG turn event with updated JSONL schema.
        
        Args:
            request_id: Unique request identifier (UUID v4)
            lane: RAG lane (fast/accurate)
            query: User query (will be redacted if REDACT_LOGS=1)
            topk: Number of results requested
            stages: Stage timing {retrieve_ms, rerank_ms, synth_ms, total_ms}
            grounding_score: Overall grounding score 0..1 (null if not computed)
            stones: List of expected stones/principles (null if not available)
            citations: Citations array with source_id and span info
            flags: RAG flags {rag_enabled, fallback}
            trace: Optional debug info (kept small)
        """
        if not self.enabled or not self._should_sample():
            return
        
        try:
            # Build event with new JSONL schema
            event = {
                "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),  # Second precision
                "request_id": request_id,
                "lane": lane,
                "topk": topk,
                "stones": stones,
                "grounding_score": grounding_score,
                "stages": stages,
                "flags": flags or {"rag_enabled": True, "fallback": None},
                "citations": citations or [],
                "trace": trace
            }
            
            # Handle query redaction - only redact the query field if redaction is enabled
            if self.redact:
                event["query"] = self._redact_query(query)
            else:
                # Include truncated query for development
                event["query"] = self._truncate_text(query)
            
            # Apply full redaction before writing (preserves existing redaction system)
            redactor = get_redactor()
            redacted_event = redactor.redact_dict(event)
            
            # Write to log file
            log_file = self._get_log_file_path()
            # Ensure directory exists before writing
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "a", buffering=1) as f:  # Line buffering
                f.write(json.dumps(redacted_event, separators=(',', ':')) + "\n")
                
        except Exception as e:
            # Never break the product flow
            logger.warning(f"Failed to log RAG turn: {e}")


# Global instance
_rag_obs = RAGObservability()


def log_rag_turn(request_id: str,
                lane: str,
                query: str,
                topk: int,
                stages: Dict[str, int],
                grounding_score: Optional[float] = None,
                stones: Optional[List[str]] = None,
                citations: Optional[List[Dict[str, Any]]] = None,
                flags: Optional[Dict[str, Any]] = None,
                trace: Optional[Dict[str, Any]] = None) -> None:
    """Log a RAG turn event using the global observability instance."""
    _rag_obs.log_rag_turn(request_id, lane, query, topk, stages, grounding_score, stones, citations, flags, trace)
