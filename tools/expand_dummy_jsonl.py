#!/usr/bin/env python3
"""
Expand dummy JSONL files to split "lane":"both" entries into separate "fast" and "accurate" entries.

This script reads dummy_retrieval.jsonl and dummy_answers.jsonl files and expands any entries
with "lane":"both" into two separate entries with "lane":"fast" and "lane":"accurate".
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Tuple


def process_jsonl_file(file_path: Path) -> Tuple[int, int, int]:
    """
    Process a single JSONL file to expand "lane":"both" entries.
    
    Args:
        file_path: Path to the JSONL file to process
        
    Returns:
        Tuple of (input_count, output_count, expanded_count)
    """
    if not file_path.exists():
        print(f"⚠️ File not found: {file_path}")
        return 0, 0, 0
    
    # Create backup if it doesn't exist
    backup_path = file_path.with_suffix(file_path.suffix + '.bak')
    if not backup_path.exists():
        print(f"📁 Creating backup: {backup_path}")
        with open(file_path, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    
    input_count = 0
    output_count = 0
    expanded_count = 0
    
    # Process file - read entire content and split by complete JSON objects
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.tmp') as temp_file:
        temp_path = Path(temp_file.name)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split content into individual JSON objects
            # Look for patterns like "}{" to identify object boundaries
            json_objects = []
            current_obj = ""
            brace_count = 0
            in_string = False
            escape_next = False
            
            for char in content:
                if escape_next:
                    escape_next = False
                    current_obj += char
                    continue
                
                if char == '\\':
                    escape_next = True
                    current_obj += char
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    current_obj += char
                    continue
                
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                
                current_obj += char
                
                # If we've closed all braces and we're not in a string, we have a complete object
                if brace_count == 0 and not in_string and current_obj.strip():
                    json_objects.append(current_obj.strip())
                    current_obj = ""
            
            # Process each JSON object
            for obj_str in json_objects:
                if not obj_str:  # Skip empty objects
                    continue
                
                try:
                    data = json.loads(obj_str)
                    input_count += 1
                    
                    # Check if lane is "both"
                    if data.get("lane") == "both":
                        # Create fast version
                        fast_data = data.copy()
                        fast_data["lane"] = "fast"
                        temp_file.write(json.dumps(fast_data, separators=(',', ':')) + '\n')
                        output_count += 1
                        
                        # Create accurate version
                        accurate_data = data.copy()
                        accurate_data["lane"] = "accurate"
                        temp_file.write(json.dumps(accurate_data, separators=(',', ':')) + '\n')
                        output_count += 1
                        
                        expanded_count += 1
                    else:
                        # Pass through unchanged (but normalize to single line)
                        temp_file.write(json.dumps(data, separators=(',', ':')) + '\n')
                        output_count += 1
                        
                except json.JSONDecodeError as e:
                    print(f"❌ JSON parse error in {file_path}: {e}")
                    print(f"   Object content: {obj_str[:200]}...")
                    raise
        
        except Exception as e:
            # Clean up temp file on error
            temp_path.unlink(missing_ok=True)
            raise
    
    # Atomically replace original file
    temp_path.replace(file_path)
    
    return input_count, output_count, expanded_count


def main():
    """Main function to process dummy JSONL files."""
    # Default file paths
    retrieval_file = Path("eval/data/dummy_retrieval.jsonl")
    answers_file = Path("eval/data/dummy_answers.jsonl")
    
    print("🔧 Expanding dummy JSONL files...")
    print()
    
    total_input = 0
    total_output = 0
    total_expanded = 0
    
    # Process retrieval file
    if retrieval_file.exists():
        print(f"📄 Processing: {retrieval_file}")
        input_count, output_count, expanded_count = process_jsonl_file(retrieval_file)
        print(f"   Input: {input_count} lines")
        print(f"   Output: {output_count} lines")
        print(f"   Expanded: {expanded_count} 'both' entries")
        print()
        
        total_input += input_count
        total_output += output_count
        total_expanded += expanded_count
    else:
        print(f"⚠️ File not found: {retrieval_file}")
        print()
    
    # Process answers file (optional)
    if answers_file.exists():
        print(f"📄 Processing: {answers_file}")
        input_count, output_count, expanded_count = process_jsonl_file(answers_file)
        print(f"   Input: {input_count} lines")
        print(f"   Output: {output_count} lines")
        print(f"   Expanded: {expanded_count} 'both' entries")
        print()
        
        total_input += input_count
        total_output += output_count
        total_expanded += expanded_count
    else:
        print(f"ℹ️ Optional file not found: {answers_file}")
        print()
    
    # Summary
    print("📊 Summary:")
    print(f"   Total input lines: {total_input}")
    print(f"   Total output lines: {total_output}")
    print(f"   Total expanded entries: {total_expanded}")
    
    if total_expanded > 0:
        print(f"✅ Successfully expanded {total_expanded} 'both' entries into {total_expanded * 2} lane-specific entries")
    else:
        print("ℹ️ No 'both' entries found to expand")


if __name__ == "__main__":
    main()
