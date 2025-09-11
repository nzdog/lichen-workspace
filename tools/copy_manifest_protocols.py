#!/usr/bin/env python3
"""
Copy all protocols from a manifest file to a new test-protocols folder.

This script reads a manifest file (YAML or JSON) and copies all the protocol
files listed in the manifest to a new directory for testing purposes.
"""

import json
import yaml
import shutil
import argparse
from pathlib import Path
from typing import Dict, List


def load_manifest(manifest_path: Path) -> Dict:
    """Load manifest from YAML or JSON file."""
    with open(manifest_path, 'r', encoding='utf-8') as f:
        if manifest_path.suffix.lower() in ['.yaml', '.yml']:
            return yaml.safe_load(f)
        elif manifest_path.suffix.lower() == '.json':
            return json.load(f)
        else:
            raise ValueError(f"Unsupported manifest format: {manifest_path.suffix}")


def copy_protocols_from_manifest(manifest_path: Path, output_dir: Path) -> None:
    """Copy all protocols from manifest to output directory."""
    
    # Load manifest
    manifest = load_manifest(manifest_path)
    items = manifest.get('items', [])
    
    if not items:
        print("No items found in manifest")
        return
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Copying {len(items)} protocols from manifest...")
    print(f"Source manifest: {manifest_path}")
    print(f"Destination: {output_dir}")
    print()
    
    copied_count = 0
    skipped_count = 0
    errors = []
    
    for item in items:
        source_path = Path(item['path'])
        protocol_id = item['protocol_id']
        title = item['title']
        
        # Create destination filename (use protocol_id to avoid conflicts)
        dest_filename = f"{protocol_id}.json"
        dest_path = output_dir / dest_filename
        
        try:
            # Copy the file
            if source_path.exists():
                shutil.copy2(source_path, dest_path)
                copied_count += 1
                print(f"✅ Copied: {title} -> {dest_filename}")
            else:
                skipped_count += 1
                errors.append(f"Source file not found: {source_path}")
                print(f"❌ Skipped: {title} (file not found: {source_path})")
                
        except Exception as e:
            skipped_count += 1
            errors.append(f"Error copying {source_path}: {e}")
            print(f"❌ Error: {title} - {e}")
    
    print()
    print(f"📊 Copy Summary:")
    print(f"  ✅ Successfully copied: {copied_count}")
    print(f"  ❌ Skipped/Errors: {skipped_count}")
    print(f"  📁 Output directory: {output_dir}")
    
    if errors:
        print()
        print("🚨 Errors encountered:")
        for error in errors:
            print(f"  - {error}")


def main():
    parser = argparse.ArgumentParser(description="Copy protocols from manifest to test directory")
    parser.add_argument("--manifest", 
                       default="manifests/canon_batch_2025-09-11.yaml",
                       help="Path to manifest file (YAML or JSON)")
    parser.add_argument("--output", 
                       default="test-protocols",
                       help="Output directory for copied protocols")
    parser.add_argument("--latest", 
                       action="store_true",
                       help="Use the latest manifest file from manifests/ directory")
    
    args = parser.parse_args()
    
    # Determine manifest path
    if args.latest:
        manifests_dir = Path("manifests")
        manifest_files = list(manifests_dir.glob("canon_batch_*.yaml")) + list(manifests_dir.glob("canon_batch_*.json"))
        if not manifest_files:
            print("❌ No manifest files found in manifests/ directory")
            return
        manifest_path = max(manifest_files, key=lambda p: p.stat().st_mtime)
        print(f"📄 Using latest manifest: {manifest_path}")
    else:
        manifest_path = Path(args.manifest)
    
    # Check if manifest exists
    if not manifest_path.exists():
        print(f"❌ Manifest file not found: {manifest_path}")
        return
    
    # Set up output directory
    output_dir = Path(args.output)
    
    # Copy protocols
    copy_protocols_from_manifest(manifest_path, output_dir)


if __name__ == "__main__":
    main()
