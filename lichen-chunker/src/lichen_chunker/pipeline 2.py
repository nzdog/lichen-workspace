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


def resolve_profile(profile: str, sidebar_overrides: dict = None) -> dict:
    """
    Resolve configuration based on profile with optional sidebar overrides.
    
    Args:
        profile: Either "speed" or "accuracy" 
        sidebar_overrides: Optional dict of parameter overrides from UI
    
    Returns:
        Dict with resolved configuration
    """
    # Base profiles
    profiles = {
        "speed": {
            "validation": False,
            "max_tokens": 1000,
            "overlap_tokens": 100,
            "backend": "sbert",
            "save_chunks": False,
            "duplicate_check": False,
            "flatten_fields": True,
            "minimal_normalization": True,
            "sentence_aware": False
        },
        "accuracy": {
            "validation": True,
            "max_tokens": 600,
            "overlap_tokens": 60,
            "backend": "openai",
            "save_chunks": True,
            "duplicate_check": True,
            "flatten_fields": False,
            "minimal_normalization": False,
            "sentence_aware": True,
            "add_breadcrumbs": True
        }
    }
    
    if profile not in profiles:
        raise ValueError(f"Unknown profile: {profile}. Must be 'speed' or 'accuracy'")
    
    config = profiles[profile].copy()
    
    # Apply sidebar overrides if provided
    if sidebar_overrides:
        config.update(sidebar_overrides)
    
    return config


class ProcessingPipeline:
    """Main pipeline for processing Lichen Protocol files."""
    
    def __init__(
        self,
        embedding_backend: Optional[EmbeddingBackend] = None,
        max_tokens: int = 600,
        overlap_tokens: int = 60,
        index_path: Optional[Path] = None,
        validation: bool = True,
        save_chunks: bool = True,
        duplicate_check: bool = True,
        profile: Optional[str] = None,
        eval_mode: bool = False,
        flatten_fields: bool = False,
        minimal_normalization: bool = False,
        sentence_aware: bool = False,
        add_breadcrumbs: bool = False
    ):
        """
        Initialize pipeline.
        
        Args:
            embedding_backend: Backend for embeddings (auto-detected if None)
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of tokens to overlap
            index_path: Path to store index (defaults to ./index)
            validation: Whether to validate against schema
            save_chunks: Whether to save chunk files to disk
            duplicate_check: Whether to check for duplicate chunks
            profile: Profile name for storage path organization
            flatten_fields: Whether to flatten long fields (speed profile)
            minimal_normalization: Whether to use minimal normalization (speed profile)
            sentence_aware: Whether to use sentence-aware splitting (accuracy profile)
            add_breadcrumbs: Whether to add breadcrumb lines (accuracy profile)
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.validation = validation
        self.save_chunks = save_chunks
        self.duplicate_check = duplicate_check
        self.profile = profile
        self.eval_mode = eval_mode
        self.flatten_fields = flatten_fields
        self.minimal_normalization = minimal_normalization
        self.sentence_aware = sentence_aware
        self.add_breadcrumbs = add_breadcrumbs
        
        # Set up profile-specific paths
        base_index_path = index_path or Path("./index")
        if profile:
            if eval_mode:
                # In eval mode, map speed->fast, accuracy->accurate and use .vector/
                lane_name = "fast" if profile == "speed" else "accurate"
                self.index_path = base_index_path / lane_name
            else:
                self.index_path = base_index_path / profile
        else:
            self.index_path = base_index_path
        
        # Initialize embedding backend
        if embedding_backend is None:
            self.embedding_backend = self._create_embedding_backend()
        else:
            self.embedding_backend = embedding_backend
        
        # Initialize indexer
        self.indexer = create_indexer(self.index_path, self.embedding_backend, eval_mode)
    
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
            
            # Validate the protocol data (only if validation is enabled)
            if self.validation:
                is_valid, errors = validate_protocol_json(protocol_data, schema_path)
                
                if not is_valid:
                    return ProcessingResult(
                        file_path=str(abs_path),
                        protocol_id=protocol_id,
                        valid=False,
                        error_message="; ".join(errors)
                    )
            else:
                # Skip validation in speed mode
                is_valid = True
            
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
            
            # Chunk protocol with profile-specific settings
            chunker = ProtocolChunker(
                max_tokens=self.max_tokens,
                overlap_tokens=self.overlap_tokens,
                flatten_fields=self.flatten_fields,
                minimal_normalization=self.minimal_normalization,
                sentence_aware=self.sentence_aware,
                add_breadcrumbs=self.add_breadcrumbs
            )
            chunks = chunker.chunk_protocol(protocol, abs_path, protocol_id)
            
            # Add profile metadata to chunks
            if self.profile:
                for chunk in chunks:
                    chunk.metadata.profile = self.profile
            
            # Save chunks (only if save_chunks is enabled)
            chunks_file = None
            if self.save_chunks:
                # Use profile-specific output directory
                if self.profile:
                    profile_output_dir = output_dir / self.profile
                    profile_output_dir.mkdir(parents=True, exist_ok=True)
                    chunks_file = profile_output_dir / f"{protocol_id}.chunks.jsonl"
                else:
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
                chunks_file=str(chunks_file) if chunks_file else None
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


def hybrid_search(
    query: str,
    k: int = 5,
    base_index_path: Path = Path("./index"),
    k_rrf: int = 60,
    weight_blend: Optional[Tuple[float, float]] = None,
    filters: Optional[Dict[str, Any]] = None
) -> List[SearchResult]:
    """
    Perform hybrid search across both speed and accuracy indexes.
    
    Args:
        query: Search query
        k: Number of results to return
        base_index_path: Base path to index directories
        k_rrf: RRF parameter (lower = more emphasis on rank)
        weight_blend: Optional weight blend (speed_weight, accuracy_weight)
        filters: Optional filters
        
    Returns:
        List of fused and de-duplicated search results
    """
    from .indexer import create_indexer
    from .embeddings import SBERTEmbedder, OpenAIEmbedder
    
    # Load both indexes
    speed_path = base_index_path / "speed"
    accuracy_path = base_index_path / "accuracy"
    
    if not speed_path.exists() or not accuracy_path.exists():
        raise ValueError("Both speed and accuracy indexes must exist for hybrid search")
    
    # Create indexers for both profiles
    # Try to detect backend from existing indexes
    try:
        speed_indexer = create_indexer(speed_path, SBERTEmbedder())
        accuracy_indexer = create_indexer(accuracy_path, OpenAIEmbedder())
    except Exception:
        # Fallback to SBERT for both
        speed_indexer = create_indexer(speed_path, SBERTEmbedder())
        accuracy_indexer = create_indexer(accuracy_path, SBERTEmbedder())
    
    # Search both indexes
    speed_results = speed_indexer.search(query, k=k, filters=filters)
    accuracy_results = accuracy_indexer.search(query, k=k, filters=filters)
    
    # Apply fusion
    if weight_blend:
        fused_results = _weight_blend_fusion(speed_results, accuracy_results, weight_blend, k)
    else:
        fused_results = _rrf_fusion(speed_results, accuracy_results, k_rrf, k)
    
    return fused_results


def _rrf_fusion(
    speed_results: List[SearchResult], 
    accuracy_results: List[SearchResult], 
    k_rrf: int, 
    top_k: int
) -> List[SearchResult]:
    """Apply Reciprocal Rank Fusion (RRF)."""
    # Create mapping of chunk_id to results from both lanes
    result_map = {}
    
    # Add speed results with RRF score
    for rank, result in enumerate(speed_results):
        chunk_id = result.metadata.chunk_id
        rrf_score = 1.0 / (k_rrf + rank + 1)
        
        if chunk_id not in result_map:
            result_map[chunk_id] = {
                'result': result,
                'speed_rank': rank + 1,
                'accuracy_rank': None,
                'rrf_score': rrf_score
            }
        else:
            result_map[chunk_id]['speed_rank'] = rank + 1
            result_map[chunk_id]['rrf_score'] += rrf_score
    
    # Add accuracy results with RRF score
    for rank, result in enumerate(accuracy_results):
        chunk_id = result.metadata.chunk_id
        rrf_score = 1.0 / (k_rrf + rank + 1)
        
        if chunk_id not in result_map:
            result_map[chunk_id] = {
                'result': result,
                'speed_rank': None,
                'accuracy_rank': rank + 1,
                'rrf_score': rrf_score
            }
        else:
            result_map[chunk_id]['accuracy_rank'] = rank + 1
            result_map[chunk_id]['rrf_score'] += rrf_score
    
    # Sort by RRF score and take top-k
    sorted_results = sorted(result_map.values(), key=lambda x: x['rrf_score'], reverse=True)
    
    # Create final results with fused scores
    fused_results = []
    for item in sorted_results[:top_k]:
        result = item['result']
        result.score = item['rrf_score']  # Replace with RRF score
        result.metadata.fusion_info = {
            'speed_rank': item['speed_rank'],
            'accuracy_rank': item['accuracy_rank'],
            'rrf_score': item['rrf_score']
        }
        fused_results.append(result)
    
    return fused_results


def _weight_blend_fusion(
    speed_results: List[SearchResult], 
    accuracy_results: List[SearchResult], 
    weights: Tuple[float, float], 
    top_k: int
) -> List[SearchResult]:
    """Apply weighted blend fusion."""
    speed_weight, accuracy_weight = weights
    result_map = {}
    
    # Add speed results with weighted score
    for result in speed_results:
        chunk_id = result.metadata.chunk_id
        weighted_score = result.score * speed_weight
        
        if chunk_id not in result_map:
            result_map[chunk_id] = {
                'result': result,
                'speed_score': result.score,
                'accuracy_score': None,
                'weighted_score': weighted_score
            }
        else:
            result_map[chunk_id]['speed_score'] = result.score
            result_map[chunk_id]['weighted_score'] += weighted_score
    
    # Add accuracy results with weighted score
    for result in accuracy_results:
        chunk_id = result.metadata.chunk_id
        weighted_score = result.score * accuracy_weight
        
        if chunk_id not in result_map:
            result_map[chunk_id] = {
                'result': result,
                'speed_score': None,
                'accuracy_score': result.score,
                'weighted_score': weighted_score
            }
        else:
            result_map[chunk_id]['accuracy_score'] = result.score
            result_map[chunk_id]['weighted_score'] += weighted_score
    
    # Sort by weighted score and take top-k
    sorted_results = sorted(result_map.values(), key=lambda x: x['weighted_score'], reverse=True)
    
    # Create final results with fused scores
    fused_results = []
    for item in sorted_results[:top_k]:
        result = item['result']
        result.score = item['weighted_score']  # Replace with weighted score
        result.metadata.fusion_info = {
            'speed_score': item['speed_score'],
            'accuracy_score': item['accuracy_score'],
            'weighted_score': item['weighted_score']
        }
        fused_results.append(result)
    
    return fused_results


def create_pipeline(
    backend: str = "auto",
    max_tokens: int = 600,
    overlap_tokens: int = 60,
    index_path: Optional[Path] = None,
    profile: Optional[str] = None,
    sidebar_overrides: Optional[dict] = None,
    validation: Optional[bool] = None,
    save_chunks: Optional[bool] = None,
    duplicate_check: Optional[bool] = None,
    eval_mode: bool = False
) -> ProcessingPipeline:
    """
    Create a processing pipeline.
    
    Args:
        backend: Embedding backend ("openai", "sbert", or "auto")
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Number of tokens to overlap
        index_path: Path to store index
        profile: Profile to use ("speed" or "accuracy")
        sidebar_overrides: Override settings from UI sidebar
        validation: Whether to validate against schema
        save_chunks: Whether to save chunk files to disk
        duplicate_check: Whether to check for duplicate chunks
        
    Returns:
        ProcessingPipeline instance
    """
    # If profile is provided, resolve configuration
    config = {}
    if profile:
        config = resolve_profile(profile, sidebar_overrides)
        # Profile settings take precedence
        backend = config.get("backend", backend)
        max_tokens = config.get("max_tokens", max_tokens)
        overlap_tokens = config.get("overlap_tokens", overlap_tokens)
        if validation is None:
            validation = config.get("validation", True)
        if save_chunks is None:
            save_chunks = config.get("save_chunks", True)
        if duplicate_check is None:
            duplicate_check = config.get("duplicate_check", True)
    
    # Set defaults if not specified
    if validation is None:
        validation = True
    if save_chunks is None:
        save_chunks = True  
    if duplicate_check is None:
        duplicate_check = True
    
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
        index_path=index_path,
        validation=validation,
        save_chunks=save_chunks,
        duplicate_check=duplicate_check,
        profile=profile,
        eval_mode=eval_mode,
        flatten_fields=config.get("flatten_fields", False) if profile else False,
        minimal_normalization=config.get("minimal_normalization", False) if profile else False,
        sentence_aware=config.get("sentence_aware", False) if profile else False,
        add_breadcrumbs=config.get("add_breadcrumbs", False) if profile else False
    )
