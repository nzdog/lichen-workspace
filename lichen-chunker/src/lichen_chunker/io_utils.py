"""IO utilities for file handling and safe operations."""

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Protocol ID resolution patterns and helpers
AUTO_ID_PATTERN = re.compile(r"^auto_[0-9]+(?:_[0-9]+)?$", re.IGNORECASE)


def to_snake_slug(name: str) -> str:
    """
    Convert a string to a snake_case slug.
    
    Args:
        name: Input string
        
    Returns:
        Snake case slug string
    """
    # normalize unicode, drop accents
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # keep alnum, space, dash, underscore
    s = re.sub(r"[^A-Za-z0-9 _-]+", "", s)
    # collapse spaces/dashes to underscore
    s = re.sub(r"[\s-]+", "_", s.strip())
    return s.lower()


def is_clean_stable_slug(s: str) -> bool:
    """
    Check if a string is a clean, stable slug.
    
    Args:
        s: String to check
        
    Returns:
        True if clean snake_case and not an auto ID
    """
    # clean = snake_case-ish and not an "auto_*" temp id
    return bool(re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", s)) and not AUTO_ID_PATTERN.match(s)


def create_canonical_filename(original_filename: str) -> str:
    """
    Create a canonical filename from an uploaded file.
    
    Args:
        original_filename: Original uploaded filename
        
    Returns:
        Canonical filename safe for filesystem
    """
    # Remove path components if any
    filename = Path(original_filename).name
    
    # Split name and extension
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    
    # Create safe stem using to_snake_slug but preserve more structure
    safe_stem = to_snake_slug(stem)
    
    # Ensure we don't end up with empty filename
    if not safe_stem:
        safe_stem = "unnamed_protocol"
    
    return f"{safe_stem}{suffix}"


def derive_protocol_id(file_path: str, obj: Dict) -> Tuple[str, bool]:
    """
    Derive a deterministic protocol_id from filename and existing data.
    
    Args:
        file_path: Path to the protocol file
        obj: Parsed protocol JSON object
        
    Returns:
        Tuple of (protocol_id, changed) where changed indicates if ID was modified
        
    Rules:
      - If JSON has a clean, stable 'Protocol ID', keep it.
      - Else derive from filename (stem) with to_snake_slug().
    """
    existing = (obj.get("Protocol ID") or "").strip()
    file_slug = to_snake_slug(Path(file_path).stem)

    if existing and is_clean_stable_slug(existing):
        # If it already equals the file slug, definitely keep.
        # If it's a different clean slug, prefer explicit JSON id.
        return existing, False

    # Replace temp/auto/empty with filename-derived slug
    return file_slug, existing != file_slug


def safe_filename(name: str) -> str:
    """
    Convert a string to a safe filename.
    
    Args:
        name: Input string
        
    Returns:
        Safe filename string
    """
    # Remove or replace unsafe characters
    safe = re.sub(r'[^\w\-_.]', '_', name)
    # Remove multiple underscores
    safe = re.sub(r'_+', '_', safe)
    # Remove leading/trailing underscores
    safe = safe.strip('_')
    # Ensure it's not empty
    if not safe:
        safe = "unnamed"
    return safe.lower()


def load_json(file_path: Path) -> Dict[str, Any]:
    """
    Load JSON from file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Dict[str, Any], file_path: Path) -> None:
    """
    Save data as JSON to file.
    
    Args:
        data: Data to save
        file_path: Path to save to
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """
    Load JSONL from file.
    
    Args:
        file_path: Path to JSONL file
        
    Returns:
        List of parsed JSON objects
    """
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def save_jsonl(data: List[Dict[str, Any]], file_path: Path) -> None:
    """
    Save data as JSONL to file.
    
    Args:
        data: List of dictionaries to save
        file_path: Path to save to
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def get_file_hash(file_path: Path) -> str:
    """
    Get SHA256 hash of file.
    
    Args:
        file_path: Path to file
        
    Returns:
        SHA256 hash as hex string
    """
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_text_hash(text: str) -> str:
    """
    Get SHA256 hash of text.
    
    Args:
        text: Text to hash
        
    Returns:
        SHA256 hash as hex string
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def find_files(
    directory: Path, 
    patterns: List[str], 
    recursive: bool = True
) -> List[Path]:
    """
    Find files matching patterns in directory.
    
    Args:
        directory: Directory to search
        patterns: List of glob patterns
        recursive: Whether to search recursively
        
    Returns:
        List of matching file paths
    """
    files = []
    
    if not directory.exists():
        return files
    
    for pattern in patterns:
        if recursive:
            files.extend(directory.rglob(pattern))
        else:
            files.extend(directory.glob(pattern))
    
    # Remove duplicates and sort
    return sorted(set(files))


def ensure_directory(path: Path) -> None:
    """
    Ensure directory exists.
    
    Args:
        path: Directory path
    """
    path.mkdir(parents=True, exist_ok=True)


def clean_filename(filename: str) -> str:
    """
    Clean filename for safe storage.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    # Remove other potentially problematic characters
    filename = re.sub(r'[<>:"|?*]', '_', filename)
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    # Remove leading/trailing underscores and dots
    filename = filename.strip('_.')
    # Ensure it's not empty
    if not filename:
        filename = "unnamed"
    return filename