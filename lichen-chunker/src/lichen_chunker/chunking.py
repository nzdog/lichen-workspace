"""Section-aware, token-bounded chunking for Lichen Protocols."""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import tiktoken
from tqdm import tqdm

from .io_utils import safe_filename
from .types import Chunk, ChunkMetadata, Protocol


class ChunkingError(Exception):
    """Error during chunking process."""
    pass


class ProtocolChunker:
    """Chunks Lichen Protocol JSONs into section-aware, token-bounded segments."""
    
    def __init__(
        self, 
        max_tokens: int = 600, 
        overlap_tokens: int = 60,
        encoding_name: str = "cl100k_base",
        flatten_fields: bool = False,
        minimal_normalization: bool = False,
        sentence_aware: bool = False,
        add_breadcrumbs: bool = False
    ):
        """
        Initialize chunker.
        
        Args:
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of tokens to overlap between chunks
            encoding_name: Tiktoken encoding name
            flatten_fields: Whether to flatten long fields (speed profile)
            minimal_normalization: Whether to use minimal normalization (speed profile)
            sentence_aware: Whether to use sentence-aware splitting (accuracy profile)
            add_breadcrumbs: Whether to add breadcrumb lines (accuracy profile)
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.flatten_fields = flatten_fields
        self.minimal_normalization = minimal_normalization
        self.sentence_aware = sentence_aware
        self.add_breadcrumbs = add_breadcrumbs
        
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception:
            # Fallback to simple character-based estimation
            self.encoding = None
            print("Warning: tiktoken not available, using character-based token estimation")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Rough estimation: 1 token ≈ 4 characters
            return len(text) // 4
    
    def chunk_protocol(
        self, 
        protocol: Protocol, 
        source_path: Path,
        protocol_id: Optional[str] = None
    ) -> List[Chunk]:
        """
        Chunk a protocol into sections.
        
        Args:
            protocol: The protocol to chunk
            source_path: Path to source file
            protocol_id: Protocol ID to use (derived from filename if None)
            
        Returns:
            List of chunks
        """
        if protocol_id is None:
            protocol_id = safe_filename(source_path.stem)
        
        chunks = []
        section_idx = 0
        
        # Chunk each section
        sections = self._get_sections(protocol)
        
        for section_name, section_content in sections:
            section_chunks = self._chunk_section(
                section_content,
                protocol_id=protocol_id,
                title=protocol.title,
                section_name=section_name,
                section_idx=section_idx,
                source_path=source_path,
                stones=self._extract_stones(protocol)
            )
            chunks.extend(section_chunks)
            section_idx += 1
        
        return chunks
    
    def _get_sections(self, protocol: Protocol) -> List[Tuple[str, str]]:
        """Extract sections from protocol in order."""
        sections = []
        
        # Basic protocol info
        sections.append(("Title", f"Title: {protocol.title}"))
        sections.append(("Short Title", f"Short Title: {protocol.short_title}"))
        sections.append(("Overall Purpose", f"Overall Purpose: {protocol.overall_purpose}"))
        sections.append(("Why This Matters", f"Why This Matters: {protocol.why_matters}"))
        sections.append(("When To Use This Protocol", f"When To Use This Protocol: {protocol.when_to_use}"))
        
        # Overall Outcomes
        outcomes_text = self._format_overall_outcomes(protocol.overall_outcomes)
        sections.append(("Overall Outcomes", outcomes_text))
        
        # Themes
        for i, theme in enumerate(protocol.themes):
            theme_text = self._format_theme(theme)
            sections.append((f"Theme {i+1}: {theme.name}", theme_text))
        
        # Completion Prompts
        prompts_text = "Completion Prompts:\n" + "\n".join(f"- {prompt}" for prompt in protocol.completion_prompts)
        sections.append(("Completion Prompts", prompts_text))
        
        # Optional metadata sections
        if protocol.metadata:
            if protocol.metadata.stones:
                stones_text = "Stones:\n" + "\n".join(f"- {stone}" for stone in protocol.metadata.stones)
                sections.append(("Stones", stones_text))
            
            if protocol.metadata.tags:
                tags_text = "Tags:\n" + "\n".join(f"- {tag}" for tag in protocol.metadata.tags)
                sections.append(("Tags", tags_text))
        
        return sections
    
    def _format_overall_outcomes(self, outcomes) -> str:
        """Format overall outcomes section."""
        text = "Overall Outcomes:\n"
        text += f"Poor: {outcomes.poor}\n"
        text += f"Expected: {outcomes.expected}\n"
        text += f"Excellent: {outcomes.excellent}\n"
        text += f"Transcendent: {outcomes.transcendent}"
        return text
    
    def _format_theme(self, theme) -> str:
        """Format a theme section."""
        text = f"Theme: {theme.name}\n"
        text += f"Purpose: {theme.purpose}\n"
        text += f"Why This Matters: {theme.why_matters}\n\n"
        
        # Outcomes
        text += "Outcomes:\n"
        for level in ["poor", "expected", "excellent", "transcendent"]:
            outcome = getattr(theme.outcomes, level)
            text += f"{level.title()}:\n"
            text += f"  Present pattern: {outcome.present_pattern}\n"
            text += f"  Immediate cost: {outcome.immediate_cost}\n"
            text += f"  30-90 day system effect: {outcome.system_effect_30_90}\n"
            text += f"  Signals: {outcome.signals}\n"
            text += f"  Edge condition: {outcome.edge_condition}\n"
            text += f"  Example moves: {outcome.example_moves}\n"
            text += f"  Future effect: {outcome.future_effect}\n\n"
        
        # Guiding Questions
        text += "Guiding Questions:\n"
        for i, question in enumerate(theme.guiding_questions, 1):
            text += f"{i}. {question}\n"
        
        return text
    
    def _chunk_section(
        self,
        content: str,
        protocol_id: str,
        title: str,
        section_name: str,
        section_idx: int,
        source_path: Path,
        stones: List[str]
    ) -> List[Chunk]:
        """Chunk a single section into token-bounded segments."""
        chunks = []
        
        # If content fits in one chunk, return it
        if self.count_tokens(content) <= self.max_tokens:
            chunk = self._create_chunk(
                content, protocol_id, title, section_name, section_idx, 0, source_path, stones
            )
            return [chunk]
        
        # Split into overlapping chunks
        sentences = self._split_into_sentences(content)
        current_chunk = ""
        chunk_idx = 0
        
        for sentence in sentences:
            test_chunk = current_chunk + sentence + "\n"
            
            if self.count_tokens(test_chunk) > self.max_tokens and current_chunk:
                # Create chunk from current content
                chunk = self._create_chunk(
                    current_chunk.strip(), protocol_id, title, section_name, section_idx, chunk_idx, source_path, stones
                )
                chunks.append(chunk)
                chunk_idx += 1
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + sentence + "\n"
            else:
                current_chunk = test_chunk
        
        # Add final chunk
        if current_chunk.strip():
            chunk = self._create_chunk(
                current_chunk.strip(), protocol_id, title, section_name, section_idx, chunk_idx, source_path, stones
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting - could be improved with nltk
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from the end of previous chunk."""
        if not text:
            return ""
        
        # Get last few sentences for overlap
        sentences = self._split_into_sentences(text)
        overlap_sentences = []
        overlap_tokens = 0
        
        for sentence in reversed(sentences):
            if overlap_tokens + self.count_tokens(sentence) > self.overlap_tokens:
                break
            overlap_sentences.insert(0, sentence)
            overlap_tokens += self.count_tokens(sentence)
        
        return " ".join(overlap_sentences) + "\n" if overlap_sentences else ""
    
    def _create_chunk(
        self,
        text: str,
        protocol_id: str,
        title: str,
        section_name: str,
        section_idx: int,
        chunk_idx: int,
        source_path: Path,
        stones: List[str]
    ) -> Chunk:
        """Create a chunk with metadata using the resolved protocol_id."""
        chunk_id = f"{protocol_id}::s{section_idx}::c{chunk_idx}"
        n_tokens = self.count_tokens(text)
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        created_at = datetime.now().isoformat()
        
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            protocol_id=protocol_id,
            title=title,
            section_name=section_name,
            section_idx=section_idx,
            chunk_idx=chunk_idx,
            n_tokens=n_tokens,
            source_path=str(source_path.absolute()),
            stones=stones,
            created_at=created_at,
            hash=text_hash
        )
        
        return Chunk(text=text, metadata=metadata)
    
    def _extract_stones(self, protocol: Protocol) -> List[str]:
        """Extract stones from protocol metadata."""
        if protocol.metadata and protocol.metadata.stones:
            return protocol.metadata.stones
        return []


def chunk_protocol_file(
    file_path: Path,
    output_dir: Path,
    max_tokens: int = 600,
    overlap_tokens: int = 60,
    protocol_id: Optional[str] = None
) -> Tuple[bool, List[str], Optional[List[Chunk]]]:
    """
    Chunk a protocol file and save results.
    
    Args:
        file_path: Path to protocol JSON file
        output_dir: Directory to save chunks
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Number of tokens to overlap
        protocol_id: Protocol ID to use
        
    Returns:
        Tuple of (success, error_messages, chunks)
    """
    try:
        from .schema_validation import validate_and_parse_protocol
        
        # Validate and parse protocol
        is_valid, errors, protocol = validate_and_parse_protocol(file_path)
        if not is_valid:
            return False, errors, None
        
        # Chunk protocol
        chunker = ProtocolChunker(max_tokens=max_tokens, overlap_tokens=overlap_tokens)
        chunks = chunker.chunk_protocol(protocol, file_path, protocol_id)
        
        # Save chunks
        output_dir.mkdir(parents=True, exist_ok=True)
        protocol_id = protocol_id or safe_filename(file_path.stem)
        chunks_file = output_dir / f"{protocol_id}.chunks.jsonl"
        
        with open(chunks_file, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                f.write(json.dumps(chunk.dict(), ensure_ascii=False) + '\n')
        
        return True, [], chunks
        
    except Exception as e:
        return False, [f"Error chunking protocol: {e}"], None