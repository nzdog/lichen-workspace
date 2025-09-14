#!/usr/bin/env python3
"""
CLI script for building protocol catalog with embeddings.

Headless re-implementation of protocol catalog building without Streamlit dependency.
"""

import argparse
import json
import glob
import re
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Set
from tqdm import tqdm
import logging

# Add rag module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.models import get_embedder

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


def load_stones_registry(stones_file: str) -> Set[str]:
    """Load Foundation Stones registry from file."""
    stones_registry = set()
    
    if not Path(stones_file).exists():
        logger.warning(f"Stones registry not found: {stones_file}")
        return stones_registry
    
    try:
        with open(stones_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract numbered headings (e.g., "1. Light Before Form")
        heading_pattern = r'^\d+\.\s+(.+)$'
        for line in content.split('\n'):
            match = re.match(heading_pattern, line.strip())
            if match:
                title = match.group(1)
                slug = slugify(title)
                stones_registry.add(slug)
        
        logger.info(f"Loaded {len(stones_registry)} Foundation Stones from {stones_file}")
        
    except Exception as e:
        logger.error(f"Error loading stones registry: {e}")
    
    return stones_registry


def extract_and_normalize_stones(protocol_data: Dict[str, Any], stones_registry: Set[str]) -> List[str]:
    """Extract and normalize stones, validating against registry."""
    stones = protocol_data.get("Metadata", {}).get("Stones", [])
    if not isinstance(stones, list):
        return []
    
    normalized_stones = []
    for stone in stones:
        if isinstance(stone, str):
            # Normalize the stone slug
            normalized = stone.strip().lower().replace(' ', '-')
            # Remove non-alphanumeric characters except hyphens
            normalized = re.sub(r'[^a-z0-9\-]', '', normalized)
            # Remove multiple consecutive hyphens
            normalized = re.sub(r'-+', '-', normalized).strip('-')
            
            # Validate against registry
            if normalized in stones_registry:
                normalized_stones.append(normalized)
            else:
                logger.debug(f"Stone '{stone}' (normalized: '{normalized}') not found in registry")
    
    return normalized_stones


def extract_key_phrases(protocol_data: Dict[str, Any]) -> List[str]:
    """Extract comprehensive key phrases from protocol data."""
    phrases = []

    # 1. HIGH PRIORITY: Theme names (very important)
    themes = protocol_data.get("Themes", [])
    for theme in themes:
        theme_name = theme.get("Name", "")
        if theme_name:
            phrases.append(theme_name.lower())
            # Also add individual words from theme names
            phrases.extend(theme_name.lower().split())

    # 2. HIGH PRIORITY: "When To Use This Protocol" field
    when_to_use = protocol_data.get("When To Use This Protocol", "")
    if when_to_use:
        # Extract key terms from usage description
        key_terms = extract_key_terms(when_to_use)
        phrases.extend(key_terms)

    # 3. HIGH PRIORITY: Overall Purpose key terms
    purpose = protocol_data.get("Overall Purpose", "")
    if purpose:
        key_terms = extract_key_terms(purpose)
        phrases.extend(key_terms)

    # 4. MEDIUM PRIORITY: Theme purposes and descriptions
    for theme in themes:
        theme_purpose = theme.get("Purpose of This Theme", "")
        if theme_purpose:
            key_terms = extract_key_terms(theme_purpose)
            phrases.extend(key_terms)

        why_matters = theme.get("Why This Matters", "")
        if why_matters:
            key_terms = extract_key_terms(why_matters)
            phrases.extend(key_terms)

    # 5. MEDIUM PRIORITY: Overall Outcomes key phrases
    overall_outcomes = protocol_data.get("Overall Outcomes", {})
    for outcome_type, outcome_text in overall_outcomes.items():
        if isinstance(outcome_text, str):
            key_terms = extract_key_terms(outcome_text)
            phrases.extend(key_terms)

    # 6. LOW PRIORITY: Guiding questions (first few words)
    for theme in themes:
        questions = theme.get("Guiding Questions", [])
        for question in questions:
            # Extract first 3-4 words as key phrase
            words = question.split()[:4]
            if len(words) >= 2:
                phrases.append(" ".join(words).lower())

    # 7. Extract from metadata stones/fields/tags
    metadata = protocol_data.get("Metadata", {})
    for field_name in ["Stones", "Fields", "Tags"]:
        field_values = metadata.get(field_name, [])
        if isinstance(field_values, list):
            phrases.extend([str(v).lower() for v in field_values])

    # Clean and deduplicate
    cleaned_phrases = []
    for phrase in phrases:
        if isinstance(phrase, str) and len(phrase.strip()) > 2:
            cleaned = phrase.strip().lower()
            # Skip very common words
            if cleaned not in ['the', 'and', 'for', 'you', 'this', 'that', 'with', 'from']:
                cleaned_phrases.append(cleaned)

    # Deduplicate and limit
    unique_phrases = list(set(cleaned_phrases))
    return unique_phrases[:30]  # Limit to 30 key phrases


def extract_key_terms(text: str) -> List[str]:
    """Extract key terms from text using simple NLP rules."""
    if not text:
        return []

    terms = []
    text = text.lower()

    # Split into sentences and words
    words = re.findall(r'\b\w+\b', text)

    # Extract meaningful words (length > 3, not common words)
    stop_words = {'the', 'and', 'for', 'you', 'this', 'that', 'with', 'from', 'when', 'what', 
                  'where', 'why', 'how', 'they', 'have', 'been', 'will', 'your', 'are', 'can', 
                  'may', 'should', 'would'}

    for word in words:
        if len(word) > 3 and word not in stop_words:
            terms.append(word)

    # Extract 2-word phrases for better matching
    for i in range(len(words) - 1):
        if len(words[i]) > 2 and len(words[i + 1]) > 2:
            if words[i] not in stop_words and words[i + 1] not in stop_words:
                phrase = f"{words[i]} {words[i + 1]}"
                terms.append(phrase)

    return terms[:15]  # Limit key terms per text


def extract_snippet(text: str, max_words: int = 20) -> str:
    """Extract first N words from text."""
    if not text:
        return ""
    
    words = text.split()
    if len(words) <= max_words:
        return text
    
    return " ".join(words[:max_words]) + "..."


def generate_protocol_embedding(protocol_data: Dict[str, Any], embedder_model) -> List[float]:
    """Generate embedding for a protocol from multiple text components."""
    texts_to_embed = []
    
    # Add title
    title = protocol_data.get("Title", "")
    if title:
        texts_to_embed.append(title)
    
    # Add short title if different
    short_title = protocol_data.get("Short Title", "")
    if short_title and short_title != title:
        texts_to_embed.append(short_title)
    
    # Add why snippet (first ~20 words)
    why_matters = protocol_data.get("Why This Matters", "")
    if why_matters:
        why_snippet = extract_snippet(why_matters, 20)
        texts_to_embed.append(why_snippet)
    
    # Add stones (convert slugs to readable text)
    stones = extract_and_normalize_stones(protocol_data, set())
    for stone in stones:
        texts_to_embed.append(stone.replace("-", " "))
    
    # Add tags
    tags = protocol_data.get("Metadata", {}).get("Tags", [])
    for tag in tags:
        if isinstance(tag, str):
            texts_to_embed.append(tag)
    
    # Add fields
    fields = protocol_data.get("Metadata", {}).get("Fields", [])
    for field in fields:
        if isinstance(field, str):
            texts_to_embed.append(field)
    
    # Add bridges
    bridges = protocol_data.get("Metadata", {}).get("Bridges", [])
    for bridge in bridges:
        if isinstance(bridge, str):
            texts_to_embed.append(bridge)
    
    # Add key phrases
    key_phrases = extract_key_phrases(protocol_data)
    for phrase in key_phrases:
        if isinstance(phrase, str):
            texts_to_embed.append(phrase)
    
    # Add top theme names
    themes = protocol_data.get("Themes", [])
    for theme in themes[:3]:  # Top 3 themes
        theme_name = theme.get("Name", "")
        if theme_name:
            texts_to_embed.append(theme_name)
    
    if not texts_to_embed:
        # Fallback to protocol_id
        protocol_id = protocol_data.get("Protocol ID", "")
        if protocol_id:
            texts_to_embed = [protocol_id]
        else:
            return []
    
    try:
        # Generate embeddings for all texts
        embeddings = embedder_model.encode(texts_to_embed)
        
        # Calculate centroid (mean of all embeddings)
        centroid = embeddings.mean(axis=0)
        
        return centroid.tolist()
        
    except Exception as e:
        logger.error(f"Error generating protocol embedding: {e}")
        return []


def process_protocols(input_patterns: List[str], output_path: str, model_name: str, 
                     stones_file: str) -> Dict[str, Any]:
    """Process all protocol files and build catalog."""
    
    # Load stones registry
    stones_registry = load_stones_registry(stones_file)
    
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
    
    # Get embedder
    embedder_wrapper = get_embedder(model_name)
    embedder_model = embedder_wrapper.model
    dimension = embedder_wrapper.dimension
    
    logger.info(f"Using embedder: {model_name} (dim={dimension})")
    
    # Create output directory
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Process files
    catalog = {}
    errors = []
    start_time = time.time()
    
    for file_path in tqdm(all_files, desc="Processing protocols"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                protocol_data = json.load(f)
            
            # Extract and validate basic fields
            protocol_id = protocol_data.get("Protocol ID", slugify(Path(file_path).stem))
            title = protocol_data.get("Title", "")
            short_title = protocol_data.get("Short Title", slugify(title) if title else "")
            category = protocol_data.get("Category", "")
            
            # Extract and normalize stones
            stones = extract_and_normalize_stones(protocol_data, stones_registry)
            
            # Extract other metadata
            metadata = protocol_data.get("Metadata", {})
            tags = metadata.get("Tags", [])
            fields = metadata.get("Fields", [])
            bridges = metadata.get("Bridges", [])
            readiness_stage = metadata.get("Readiness Stage", "")
            
            # Extract why snippet
            why_matters = protocol_data.get("Why This Matters", "")
            why_snippet = extract_snippet(why_matters, 20)
            
            # Extract key phrases
            key_phrases = extract_key_phrases(protocol_data)
            
            # Generate embedding
            embedding = generate_protocol_embedding(protocol_data, embedder_model)
            
            # Create catalog entry
            entry = {
                "title": title,
                "short_title": short_title,
                "category": category,
                "stones": stones,
                "fields": fields,
                "bridges": bridges,
                "tags": tags,
                "readiness_stage": readiness_stage,
                "why_snippet": why_snippet,
                "key_phrases": key_phrases,
                "embedding": embedding
            }
            
            catalog[protocol_id] = entry
            
        except Exception as e:
            error_msg = f"Failed to process {file_path}: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            continue
    
    # Create final catalog structure
    catalog_data = {
        "model_name": model_name,
        "created_at": time.strftime('%Y-%m-%d %H:%M:%S'),
        "protocol_count": len(catalog),
        "errors_count": len(errors),
        "stones_registry": list(stones_registry),
        "catalog": catalog
    }
    
    # Save catalog
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(catalog_data, f, indent=2, ensure_ascii=False)
    
    # Calculate timing
    processing_time = time.time() - start_time
    
    # Return statistics
    stats = {
        "files_processed": len(all_files),
        "protocols_in_catalog": len(catalog),
        "errors": len(errors),
        "processing_time_seconds": processing_time,
        "model_name": model_name,
        "dimension": dimension,
        "output_file": str(output_path)
    }
    
    logger.info(f"Built catalog with {len(catalog)} protocols in {processing_time:.2f}s")
    if errors:
        logger.warning(f"Encountered {len(errors)} errors")
    
    return stats


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Build protocol catalog with embeddings")
    
    parser.add_argument("--in", nargs="+", required=True, 
                       help="Input file patterns (e.g., 'protocols/**/*.json')")
    parser.add_argument("--stones", required=True, 
                       help="Path to Foundation Stones file")
    parser.add_argument("--out", required=True, 
                       help="Output catalog JSON file")
    parser.add_argument("--model", required=True, 
                       help="Embedding model name")
    
    args = parser.parse_args()
    
    try:
        stats = process_protocols(
            input_patterns=getattr(args, 'in'),
            output_path=args.out,
            model_name=args.model,
            stones_file=args.stones
        )
        
        # Print summary
        print(f"\n✅ Protocol catalog built!")
        print(f"   Files processed: {stats['files_processed']}")
        print(f"   Protocols in catalog: {stats['protocols_in_catalog']}")
        print(f"   Processing time: {stats['processing_time_seconds']:.2f}s")
        print(f"   Model: {stats['model_name']} (dim={stats['dimension']})")
        print(f"   Output: {stats['output_file']}")
        
        if stats['errors'] > 0:
            print(f"   ⚠️  Errors: {stats['errors']}")
            sys.exit(1)
        
        # Save timing log
        timing_log = {
            "stage": "build_catalog",
            "model_name": stats['model_name'],
            "protocol_count": stats['protocols_in_catalog'],
            "dimension": stats['dimension'],
            "total_time_seconds": stats['processing_time_seconds']
        }
        
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        timing_file = logs_dir / f"catalog_timing_{int(time.time())}.json"
        with open(timing_file, 'w') as f:
            json.dump(timing_log, f, indent=2)
        
        logger.info(f"Timing log saved to: {timing_file}")
        
    except Exception as e:
        logger.error(f"Catalog building failed: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
