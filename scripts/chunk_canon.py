#!/usr/bin/env python3
"""
CLI script for chunking protocol documents.

Provides theme-aware chunking with configurable windows and metadata extraction.
"""

import argparse
import json
import glob
import re
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    if not text:
        return ""
    
    # Convert to lowercase and replace spaces with hyphens
    slug = text.lower().strip()
    slug = re.sub(r'\s+', '-', slug)
    # Remove non-alphanumeric characters except hyphens
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    return slug


def extract_themes(protocol_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract themes from protocol data."""
    themes = protocol_data.get("Themes", [])
    if not isinstance(themes, list):
        return []
    
    theme_list = []
    for theme in themes:
        if isinstance(theme, dict):
            theme_list.append({
                "name": theme.get("Name", ""),
                "slug": slugify(theme.get("Name", "")),
                "purpose": theme.get("Purpose of This Theme", ""),
                "why_matters": theme.get("Why This Matters", ""),
                "guiding_questions": theme.get("Guiding Questions", []),
                "outcomes": theme.get("Outcomes", {})
            })
    
    return theme_list


def chunk_by_themes(protocol_data: Dict[str, Any], window_size: int, overlap: int) -> List[Dict[str, Any]]:
    """
    Chunk protocol by themes, then by sentences within themes.
    
    Args:
        protocol_data: Protocol JSON data
        window_size: Maximum chunk size in characters
        overlap: Overlap between chunks in characters
        
    Returns:
        List of chunk dictionaries
    """
    chunks = []
    protocol_id = protocol_data.get("Protocol ID", "")
    themes = extract_themes(protocol_data)
    
    # If no themes, chunk the whole document
    if not themes:
        text_parts = []
        for field in ["Title", "Short Title", "Overall Purpose", "Why This Matters", "When To Use This Protocol"]:
            value = protocol_data.get(field, "")
            if value:
                text_parts.append(f"{field}: {value}")
        
        combined_text = "\n\n".join(text_parts)
        if combined_text:
            chunks.extend(_chunk_text(combined_text, window_size, overlap, protocol_id, "no-theme"))
        
        return chunks
    
    # Chunk each theme separately
    for theme in themes:
        theme_name = theme["name"]
        theme_slug = theme["slug"]
        
        # Collect text for this theme
        theme_text_parts = []
        
        # Add theme name and purpose
        if theme_name:
            theme_text_parts.append(f"Theme: {theme_name}")
        if theme["purpose"]:
            theme_text_parts.append(f"Purpose: {theme['purpose']}")
        if theme["why_matters"]:
            theme_text_parts.append(f"Why This Matters: {theme['why_matters']}")
        
        # Add guiding questions
        questions = theme.get("guiding_questions", [])
        if questions:
            questions_text = "Guiding Questions:\n" + "\n".join(f"- {q}" for q in questions)
            theme_text_parts.append(questions_text)
        
        # Add outcomes
        outcomes = theme.get("outcomes", {})
        if outcomes:
            outcomes_text = "Outcomes:\n" + "\n".join(f"- {k}: {v}" for k, v in outcomes.items())
            theme_text_parts.append(outcomes_text)
        
        # Combine theme text
        theme_text = "\n\n".join(theme_text_parts)
        
        if theme_text:
            theme_chunks = _chunk_text(theme_text, window_size, overlap, protocol_id, theme_slug)
            chunks.extend(theme_chunks)
    
    return chunks


def _chunk_text(text: str, window_size: int, overlap: int, protocol_id: str, theme_slug: str) -> List[Dict[str, Any]]:
    """Chunk text by sentences within window size."""
    if not text or len(text) <= window_size:
        if text:
            return [{
                "chunk_id": f"{protocol_id}__{theme_slug}__001",
                "text": text.strip(),
                "theme_slug": theme_slug
            }]
        return []
    
    # Split by sentences (simple approach)
    sentences = re.split(r'[.!?]+\s+', text)
    chunks = []
    current_chunk = ""
    chunk_num = 1
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # Check if adding this sentence would exceed window size
        potential_chunk = current_chunk + (" " if current_chunk else "") + sentence
        
        if len(potential_chunk) > window_size and current_chunk:
            # Save current chunk
            chunks.append({
                "chunk_id": f"{protocol_id}__{theme_slug}__{chunk_num:03d}",
                "text": current_chunk.strip(),
                "theme_slug": theme_slug
            })
            
            # Start new chunk with overlap
            overlap_text = current_chunk[-overlap:] if overlap > 0 and len(current_chunk) > overlap else ""
            current_chunk = overlap_text + (" " if overlap_text else "") + sentence
            chunk_num += 1
        else:
            current_chunk = potential_chunk
    
    # Add final chunk
    if current_chunk.strip():
        chunks.append({
            "chunk_id": f"{protocol_id}__{theme_slug}__{chunk_num:03d}",
            "text": current_chunk.strip(),
            "theme_slug": theme_slug
        })
    
    return chunks


def add_metadata(chunk: Dict[str, Any], protocol_data: Dict[str, Any], metadata_fields: List[str]) -> Dict[str, Any]:
    """Add metadata fields to chunk."""
    result = chunk.copy()
    
    for field in metadata_fields:
        if field == "protocol_id":
            result[field] = protocol_data.get("Protocol ID", "")
        elif field == "title":
            result[field] = protocol_data.get("Title", "")
        elif field == "theme_name":
            result[field] = chunk.get("theme_slug", "").replace("-", " ").title()
        elif field == "stones":
            stones = protocol_data.get("Metadata", {}).get("Stones", [])
            result[field] = stones if isinstance(stones, list) else []
        elif field == "fields":
            fields = protocol_data.get("Metadata", {}).get("Fields", [])
            result[field] = fields if isinstance(fields, list) else []
        elif field == "bridges":
            bridges = protocol_data.get("Metadata", {}).get("Bridges", [])
            result[field] = bridges if isinstance(bridges, list) else []
        elif field == "tags":
            tags = protocol_data.get("Metadata", {}).get("Tags", [])
            result[field] = tags if isinstance(tags, list) else []
        else:
            result[field] = protocol_data.get(field, "")
    
    return result


def process_protocols(input_patterns: List[str], output_path: str, window_size: int, overlap: int, 
                     by_theme: bool, metadata_fields: List[str]) -> Dict[str, Any]:
    """Process all protocol files and create chunks."""
    
    # Find all matching files
    all_files = []
    for pattern in input_patterns:
        files = glob.glob(pattern, recursive=True)
        all_files.extend(files)
    
    # Remove duplicates and sort
    all_files = sorted(list(set(all_files)))
    
    if not all_files:
        raise ValueError(f"No files found matching patterns: {input_patterns}")
    
    logger.info(f"Found {len(all_files)} protocol files")
    
    # Create output directory
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Process files
    all_chunks = []
    errors = []
    start_time = time.time()
    
    for file_path in tqdm(all_files, desc="Processing protocols"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                protocol_data = json.load(f)
            
            # Generate chunks
            if by_theme:
                chunks = chunk_by_themes(protocol_data, window_size, overlap)
            else:
                # Simple chunking - collect all text and chunk
                text_parts = []
                for field in ["Title", "Short Title", "Overall Purpose", "Why This Matters", 
                            "When To Use This Protocol"]:
                    value = protocol_data.get(field, "")
                    if value:
                        text_parts.append(f"{field}: {value}")
                
                # Add theme content
                themes = extract_themes(protocol_data)
                for theme in themes:
                    if theme["name"]:
                        text_parts.append(f"Theme: {theme['name']}")
                    if theme["purpose"]:
                        text_parts.append(f"Purpose: {theme['purpose']}")
                    if theme["why_matters"]:
                        text_parts.append(f"Why This Matters: {theme['why_matters']}")
                
                combined_text = "\n\n".join(text_parts)
                chunks = _chunk_text(combined_text, window_size, overlap, 
                                   protocol_data.get("Protocol ID", ""), "document")
            
            # Add metadata to chunks
            for chunk in chunks:
                chunk_with_meta = add_metadata(chunk, protocol_data, metadata_fields)
                all_chunks.append(chunk_with_meta)
                
        except Exception as e:
            error_msg = f"Error processing {file_path}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    # Write chunks to output file
    with open(output_path, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    # Calculate timing
    processing_time = time.time() - start_time
    
    # Return statistics
    stats = {
        "files_processed": len(all_files),
        "chunks_created": len(all_chunks),
        "errors": len(errors),
        "processing_time_seconds": processing_time,
        "window_size": window_size,
        "overlap": overlap,
        "by_theme": by_theme,
        "metadata_fields": metadata_fields,
        "output_file": str(output_path)
    }
    
    logger.info(f"Created {len(all_chunks)} chunks from {len(all_files)} files in {processing_time:.2f}s")
    if errors:
        logger.warning(f"Encountered {len(errors)} errors")
    
    return stats


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Chunk protocol documents for embedding")
    
    parser.add_argument("--in", nargs="+", required=True, 
                       help="Input file patterns (e.g., 'protocols/**/*.json')")
    parser.add_argument("--out", required=True, 
                       help="Output JSONL file path")
    parser.add_argument("--window", type=int, default=480, 
                       help="Chunk window size in characters (default: 480)")
    parser.add_argument("--overlap", type=int, default=50, 
                       help="Overlap between chunks in characters (default: 50)")
    parser.add_argument("--by-theme", action="store_true", 
                       help="Chunk by themes instead of document-level")
    parser.add_argument("--add-meta", 
                       help="Comma-separated metadata fields to add (e.g., 'protocol_id,title,stones')")
    
    args = parser.parse_args()
    
    # Parse metadata fields
    metadata_fields = []
    if args.add_meta:
        metadata_fields = [field.strip() for field in args.add_meta.split(",")]
    
    try:
        stats = process_protocols(
            input_patterns=getattr(args, 'in'),
            output_path=args.out,
            window_size=args.window,
            overlap=args.overlap,
            by_theme=args.by_theme,
            metadata_fields=metadata_fields
        )
        
        # Print summary
        print(f"\n✅ Chunking complete!")
        print(f"   Files processed: {stats['files_processed']}")
        print(f"   Chunks created: {stats['chunks_created']}")
        print(f"   Processing time: {stats['processing_time_seconds']:.2f}s")
        print(f"   Output: {stats['output_file']}")
        
        if stats['errors'] > 0:
            print(f"   ⚠️  Errors: {stats['errors']}")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Chunking failed: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
