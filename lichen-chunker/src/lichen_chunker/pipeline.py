"""Orchestration pipeline for processing Lichen Protocol files."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from tqdm import tqdm

from .chunking import ProtocolChunker, chunk_protocol_file
from .embeddings import EmbeddingBackend, OpenAIEmbedder, SBERTEmbedder
from .indexer import Indexer, create_indexer
from .io_utils import find_files, load_jsonl, load_json, save_json, derive_protocol_id
from .schema_validation import validate_protocol_json, validate_and_parse_protocol
from .types import Chunk, ProcessingResult, SearchResult


class ProcessingPipeline:
    """Main pipeline for processing Lichen Protocol files."""
    
    def __init__(
        self,
        embedding_backend: Optional[EmbeddingBackend] = None,
        max_tokens: int = 600,
        overlap_tokens: int = 60,
        index_path: Optional[Path] = None
    ):
        """
        Initialize pipeline.
        
        Args:
            embedding_backend: Backend for embeddings (auto-detected if None)
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of tokens to overlap
            index_path: Path to store index (defaults to ./index)
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.index_path = index_path or Path("./index")
        
        # Initialize embedding backend
        if embedding_backend is None:
            self.embedding_backend = self._create_embedding_backend()
        else:
            self.embedding_backend = embedding_backend
        
        # Initialize indexer
        self.indexer = create_indexer(self.index_path, self.embedding_backend)
    
    def _create_embedding_backend(self) -> EmbeddingBackend:
        """Create embedding backend based on environment."""
        load_dotenv()
        
        # Try OpenAI first if API key is available
        if os.getenv("OPENAI_API_KEY"):
            try:
                return OpenAIEmbedder()
            except Exception as e:
                print(f"Failed to create OpenAI embedder: {e}")
        
        # Fallback to SBERT
        print("Using SBERT embedding backend")
        return SBERTEmbedder()
    
    def process_files(
        self,
        file_paths: List[Path],
        output_dir: Path = Path("./data"),
        schema_path: Optional[Path] = None
    ) -> List[ProcessingResult]:
        """
        Process multiple protocol files.
        
        Args:
            file_paths: List of protocol file paths
            output_dir: Directory to save chunks
            schema_path: Path to schema file
            
        Returns:
            List of processing results
        """
        results = []
        
        for file_path in tqdm(file_paths, desc="Processing files"):
            result = self.process_file(file_path, output_dir, schema_path)
            results.append(result)
        
        return results
    
    def process_file(
        self,
        file_path: Path,
        output_dir: Path = Path("./data"),
        schema_path: Optional[Path] = None,
        protocol_id: Optional[str] = None
    ) -> ProcessingResult:
        """
        Process a single protocol file.
        
        Args:
            file_path: Path to protocol file
            output_dir: Directory to save chunks
            schema_path: Path to schema file
            protocol_id: Optional protocol ID (will be resolved deterministically if None)
            
        Returns:
            Processing result
        """
        # Use absolute path for provenance and consistent protocol_id resolution
        abs_path = file_path.resolve()
        
        try:
            
            # Load JSON first to resolve protocol_id
            protocol_data = load_json(abs_path)
            
            # Resolve protocol_id deterministically
            if protocol_id is None:
                protocol_id, changed = derive_protocol_id(str(abs_path), protocol_data)
                if changed:
                    protocol_data["Protocol ID"] = protocol_id
                    # Optionally persist the corrected Protocol ID back to disk
                    # save_json(protocol_data, file_path)
            
            # Validate the protocol data
            is_valid, errors = validate_protocol_json(protocol_data, schema_path)
            
            if not is_valid:
                return ProcessingResult(
                    file_path=str(abs_path),
                    protocol_id=protocol_id,
                    valid=False,
                    error_message="; ".join(errors)
                )
            
            # Parse protocol from validated data
            try:
                from .types import Protocol
                protocol = Protocol(**protocol_data)
            except Exception as e:
                return ProcessingResult(
                    file_path=str(abs_path),
                    protocol_id=protocol_id,
                    valid=False,
                    error_message=f"Error parsing protocol: {e}"
                )
            
            # Chunk protocol
            chunker = ProtocolChunker(
                max_tokens=self.max_tokens,
                overlap_tokens=self.overlap_tokens
            )
            chunks = chunker.chunk_protocol(protocol, abs_path, protocol_id)
            
            # Save chunks
            output_dir.mkdir(parents=True, exist_ok=True)
            chunks_file = output_dir / f"{protocol_id}.chunks.jsonl"
            
            with open(chunks_file, 'w', encoding='utf-8') as f:
                for chunk in chunks:
                    f.write(chunk.model_dump_json() + '\n')
            
            # Add to index
            self.indexer.add_chunks(chunks)
            
            return ProcessingResult(
                file_path=str(abs_path),
                protocol_id=protocol_id,
                valid=True,
                chunks_created=len(chunks),
                chunks_file=str(chunks_file)
            )
            
        except Exception as e:
            return ProcessingResult(
                file_path=str(abs_path),
                protocol_id=protocol_id or "unknown",
                valid=False,
                error_message=str(e)
            )
    
    def process_directory(
        self,
        directory: Path,
        patterns: List[str] = None,
        output_dir: Path = Path("./data"),
        schema_path: Optional[Path] = None,
        recursive: bool = True
    ) -> List[ProcessingResult]:
        """
        Process all protocol files in a directory.
        
        Args:
            directory: Directory to process
            patterns: File patterns to match (defaults to ["*.json"])
            output_dir: Directory to save chunks
            schema_path: Path to schema file
            recursive: Whether to search recursively
            
        Returns:
            List of processing results
        """
        if patterns is None:
            patterns = ["*.json"]
        
        file_paths = find_files(directory, patterns, recursive)
        return self.process_files(file_paths, output_dir, schema_path)
    
    def embed_chunks(self, chunks_files: List[Path]) -> None:
        """
        Embed chunks from JSONL files and add to index.
        
        Args:
            chunks_files: List of chunk JSONL files
        """
        for chunks_file in tqdm(chunks_files, desc="Embedding chunks"):
            chunks = load_jsonl(chunks_file)
            
            # Convert to Chunk objects
            chunk_objects = []
            for chunk_data in chunks:
                chunk = Chunk(**chunk_data)
                chunk_objects.append(chunk)
            
            # Add to index
            self.indexer.add_chunks(chunk_objects)
    
    def search(
        self,
        query: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search the index.
        
        Args:
            query: Search query
            k: Number of results to return
            filters: Optional filters
            
        Returns:
            List of search results
        """
        return self.indexer.search(query, k, filters)
    
    def save_index(self) -> None:
        """Save the index to disk."""
        self.indexer.save_index()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return self.indexer.get_stats()
    
    def clear_index(self) -> None:
        """Clear the index."""
        self.indexer.clear_index()


def create_pipeline(
    backend: str = "auto",
    max_tokens: int = 600,
    overlap_tokens: int = 60,
    index_path: Optional[Path] = None
) -> ProcessingPipeline:
    """
    Create a processing pipeline.
    
    Args:
        backend: Embedding backend ("openai", "sbert", or "auto")
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Number of tokens to overlap
        index_path: Path to store index
        
    Returns:
        ProcessingPipeline instance
    """
    embedding_backend = None
    
    if backend == "openai":
        embedding_backend = OpenAIEmbedder()
    elif backend == "sbert":
        embedding_backend = SBERTEmbedder()
    elif backend != "auto":
        raise ValueError(f"Unknown backend: {backend}")
    
    return ProcessingPipeline(
        embedding_backend=embedding_backend,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
        index_path=index_path
    )
