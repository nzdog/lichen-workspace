#!/usr/bin/env python3
"""
Validation tool for YAML prompts against the Stones registry.
"""

import sys
import yaml
import glob
from pathlib import Path


def load_stones_registry(stones_path: str = "eval/stones.yaml"):
    """Load the canonical Stones registry."""
    try:
        with open(stones_path, 'r') as f:
            data = yaml.safe_load(f)
            stones = {}
            for stone in data.get('stones', []):
                stones[stone['slug']] = stone
            return stones
    except Exception as e:
        print(f"Error: Could not load stones registry from {stones_path}: {e}")
        return None


def validate_prompts(prompts_dir: str = "eval/prompts", stones_registry: dict = None):
    """Validate all prompts against the stones registry."""
    if not stones_registry:
        print("Error: No stones registry provided")
        return False
    
    # Find all YAML files in the prompts directory
    yaml_files = glob.glob(f"{prompts_dir}/*.yaml")
    
    if not yaml_files:
        print(f"Error: No YAML files found in {prompts_dir}")
        return False
    
    print(f"Validating {len(yaml_files)} YAML files...")
    
    errors = []
    warnings = []
    total_prompts = 0
    
    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
            
            if 'prompts' not in data:
                warnings.append(f"{yaml_file}: No 'prompts' key found")
                continue
            
            for prompt in data['prompts']:
                total_prompts += 1
                query_id = prompt.get('query_id', 'unknown')
                
                # Check required fields
                required_fields = ['query_id', 'prompt', 'stone', 'stone_meaning', 'field', 'difficulty', 'assertions']
                for field in required_fields:
                    if field not in prompt:
                        errors.append(f"{query_id}: Missing required field '{field}'")
                
                # Check stone exists in registry
                if 'stone' in prompt:
                    stone_slug = prompt['stone']
                    if stone_slug not in stones_registry:
                        errors.append(f"{query_id}: Unknown stone '{stone_slug}'")
                    else:
                        # Check stone_meaning matches registry
                        if 'stone_meaning' in prompt:
                            expected_meaning = stones_registry[stone_slug]['meaning'].strip()
                            actual_meaning = prompt['stone_meaning'].strip()
                            if actual_meaning != expected_meaning:
                                errors.append(f"{query_id}: Stone meaning mismatch for '{stone_slug}'")
        
        except Exception as e:
            errors.append(f"{yaml_file}: Error loading file - {e}")
    
    # Report results
    print(f"\nValidation Results:")
    print(f"  Total prompts: {total_prompts}")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")
    
    if warnings:
        print(f"\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    if errors:
        print(f"\nErrors:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print(f"\n✅ All prompts validated successfully!")
    return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate YAML prompts against Stones registry")
    parser.add_argument("--prompts-dir", default="eval/prompts", 
                       help="Directory containing YAML prompt files")
    parser.add_argument("--stones-path", default="eval/stones.yaml",
                       help="Path to stones registry YAML file")
    
    args = parser.parse_args()
    
    # Load stones registry
    stones_registry = load_stones_registry(args.stones_path)
    if not stones_registry:
        sys.exit(1)
    
    print(f"Loaded {len(stones_registry)} stones from registry")
    
    # Validate prompts
    success = validate_prompts(args.prompts_dir, stones_registry)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
