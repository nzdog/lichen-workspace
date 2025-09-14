#!/usr/bin/env python3
"""
Protocol Cleanup Tool for Lichen Protocol MVP

Validates, fixes, and normalizes protocol JSON files against schema and template requirements.
"""

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import quote

try:
    import jsonschema
    from jsonschema import Draft202012Validator
except ImportError:
    print("Error: jsonschema package required. Install with: pip install jsonschema")
    sys.exit(2)

try:
    from tqdm import tqdm
except ImportError:
    print("Error: tqdm package required. Install with: pip install tqdm")
    sys.exit(2)


class ProtocolCleaner:
    """Main protocol cleanup and validation class."""
    
    def __init__(self, args):
        self.args = args
        self.schema = None
        self.template = None
        self.stones_slugs = set()
        self.validator = None
        self.results = {
            'run_config': {
                'protocol_glob': args.protocol_glob,
                'schema_path': args.schema_path,
                'template_path': args.template_path,
                'stones_path': args.stones_path,
                'fix_mode': args.fix,
                'strict_mode': args.strict,
                'dry_run': args.dry_run,
                'timestamp': datetime.now().isoformat()
            },
            'stones': [],
            'totals': {'total_files': 0, 'valid': 0, 'fixed': 0, 'flagged': 0, 'blocking': 0},
            'by_error': {},
            'files': []
        }
        
    def load_schema(self) -> bool:
        """Load and validate the JSON schema."""
        try:
            with open(self.args.schema_path, 'r', encoding='utf-8') as f:
                self.schema = json.load(f)
            self.validator = Draft202012Validator(self.schema)
            return True
        except Exception as e:
            print(f"Error loading schema: {e}")
            return False
    
    def load_template(self) -> bool:
        """Load the locked template to identify placeholders."""
        try:
            with open(self.args.template_path, 'r', encoding='utf-8') as f:
                self.template = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading template: {e}")
            return False
    
    def load_stones_registry(self) -> bool:
        """Load Foundation Stones registry and extract slugs."""
        try:
            stones_path = Path(self.args.stones_path)
            if stones_path.suffix == '.yaml':
                # Handle YAML format
                try:
                    import yaml
                    with open(stones_path, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    if 'stones' in data:
                        for stone in data['stones']:
                            if 'slug' in stone:
                                self.stones_slugs.add(stone['slug'])
                                self.results['stones'].append(stone)
                except ImportError:
                    print("Warning: PyYAML not available, skipping YAML stones file")
                    return False
            else:
                # Handle text format - look for numbered headings
                with open(stones_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract numbered headings (e.g., "1. Light Before Form")
                heading_pattern = r'^\d+\.\s+(.+)$'
                for line in content.split('\n'):
                    match = re.match(heading_pattern, line.strip())
                    if match:
                        title = match.group(1)
                        slug = self.slugify(title)
                        self.stones_slugs.add(slug)
                        self.results['stones'].append({'slug': slug, 'name': title})
            
            print(f"Loaded {len(self.stones_slugs)} Foundation Stones:")
            for slug in sorted(self.stones_slugs):
                print(f"  - {slug}")
            return True
        except Exception as e:
            print(f"Error loading stones registry: {e}")
            return False
    
    def slugify(self, text: str) -> str:
        """Convert text to URL-safe slug."""
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
    
    def get_protocol_files(self) -> List[Path]:
        """Get list of protocol files matching the glob pattern."""
        import glob
        files = []
        
        # Handle exclude patterns
        exclude_patterns = self.args.exclude.split(',') if self.args.exclude else []
        
        for file_path in glob.glob(self.args.protocol_glob, recursive=True):
            path = Path(file_path)
            
            # Skip if excluded
            if any(self.matches_exclude_pattern(str(path), pattern) for pattern in exclude_patterns):
                continue
            
            if path.suffix.lower() == '.json':
                files.append(path)
        
        # Sort for deterministic processing
        files.sort()
        return files
    
    def matches_exclude_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches exclude pattern."""
        import fnmatch
        pattern = pattern.strip()
        if not pattern:
            return False
        
        # Convert glob pattern to match against file path
        if '**' in pattern:
            return fnmatch.fnmatch(file_path, pattern)
        else:
            # Match against basename or full path
            return (fnmatch.fnmatch(os.path.basename(file_path), pattern) or 
                    fnmatch.fnmatch(file_path, pattern))
    
    def validate_protocol(self, file_path: Path) -> Dict[str, Any]:
        """Validate a single protocol file."""
        result = {
            'path': str(file_path),
            'issues': [],
            'fixed': [],
            'diff_preview': [],
            'status': 'unknown'
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            result['issues'].append({'code': 'JSON_PARSE', 'message': f'Invalid JSON: {e}'})
            result['status'] = 'blocking'
            return result
        except Exception as e:
            result['issues'].append({'code': 'FILE_ERROR', 'message': f'File error: {e}'})
            result['status'] = 'blocking'
            return result
        
        # Apply validation rules
        self.validate_schema(data, result)
        self.validate_placeholders(data, result)
        self.validate_themes_count(data, result)
        self.validate_completion_prompts(data, result)
        self.validate_created_at(data, result)
        self.validate_version(data, result)
        self.validate_modes(data, result)
        self.validate_stones_slugs(data, result)
        self.validate_additional_properties(data, result)
        self.validate_stable_ids(data, result, file_path)
        self.validate_when_to_use(data, result)
        
        # Apply autofixes if requested
        if self.args.fix:
            self.apply_autofixes(data, result, file_path)
        
        # Determine final status
        blocking_issues = [i for i in result['issues'] if i.get('severity') == 'blocking']
        if blocking_issues:
            result['status'] = 'blocking'
        elif result['issues']:
            result['status'] = 'flagged'
        else:
            result['status'] = 'valid'
        
        return result
    
    def validate_schema(self, data: Dict, result: Dict):
        """Validate against JSON schema."""
        try:
            errors = list(self.validator.iter_errors(data))
            if errors:
                for error in errors:
                    result['issues'].append({
                        'code': 'SCHEMA',
                        'message': f"Schema violation: {error.message} at {'.'.join(str(p) for p in error.absolute_path)}",
                        'severity': 'blocking'
                    })
        except Exception as e:
            result['issues'].append({
                'code': 'SCHEMA',
                'message': f"Schema validation error: {e}",
                'severity': 'blocking'
            })
    
    def validate_placeholders(self, data: Dict, result: Dict):
        """Check for template placeholders."""
        placeholders = [
            "[Protocol Title]", "[Q1]", "[Q2]", "[Q3]", "[Q4]", "[Q5]",
            "YYYY-MM-DD", "[Short Title]", "[Description]", "[Author]"
        ]
        
        def check_value(value, path=""):
            if isinstance(value, str):
                if value in placeholders:
                    result['issues'].append({
                        'code': 'PLACEHOLDER',
                        'message': f"Placeholder found: '{value}' at {path}",
                        'severity': 'blocking'
                    })
            elif isinstance(value, dict):
                for k, v in value.items():
                    check_value(v, f"{path}.{k}" if path else k)
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    check_value(v, f"{path}[{i}]" if path else f"[{i}]")
        
        check_value(data)
    
    def validate_themes_count(self, data: Dict, result: Dict):
        """Validate themes count is 5-7 inclusive."""
        themes = data.get('Themes', [])
        if not isinstance(themes, list):
            result['issues'].append({
                'code': 'THEMES_TYPE',
                'message': "Themes must be a list",
                'severity': 'blocking'
            })
        elif len(themes) < 5 or len(themes) > 7:
            result['issues'].append({
                'code': 'THEMES_COUNT',
                'message': f"Themes count {len(themes)} not in range 5-7",
                'severity': 'blocking'
            })
    
    def validate_completion_prompts(self, data: Dict, result: Dict):
        """Validate completion prompts count is 2-5 inclusive."""
        prompts = data.get('Completion Prompts', [])
        if not isinstance(prompts, list):
            result['issues'].append({
                'code': 'PROMPTS_TYPE',
                'message': "Completion Prompts must be a list",
                'severity': 'blocking'
            })
        elif len(prompts) < 2 or len(prompts) > 5:
            result['issues'].append({
                'code': 'PROMPTS_COUNT',
                'message': f"Completion Prompts count {len(prompts)} not in range 2-5",
                'severity': 'blocking'
            })
    
    def validate_created_at(self, data: Dict, result: Dict):
        """Validate Created At matches YYYY-MM-DD format."""
        created_at = data.get('Created At', '')
        if not isinstance(created_at, str):
            result['issues'].append({
                'code': 'CREATED_AT_TYPE',
                'message': "Created At must be a string",
                'severity': 'blocking'
            })
        elif not re.match(r'^\d{4}-\d{2}-\d{2}$', created_at):
            result['issues'].append({
                'code': 'CREATED_AT_FORMAT',
                'message': f"Created At '{created_at}' not in YYYY-MM-DD format",
                'severity': 'blocking'
            })
    
    def validate_version(self, data: Dict, result: Dict):
        """Validate version is SemVer or normalize '1' to '1.0.0'."""
        version = data.get('Version', '')
        if version == '1':
            result['issues'].append({
                'code': 'SEMVER',
                'message': "Version '1' should be '1.0.0'",
                'severity': 'fixable'
            })
        elif version and not re.match(r'^\d+\.\d+\.\d+$', version):
            result['issues'].append({
                'code': 'SEMVER',
                'message': f"Version '{version}' not valid SemVer",
                'severity': 'blocking'
            })
    
    def validate_modes(self, data: Dict, result: Dict):
        """Validate modes are subset of allowed values."""
        allowed_modes = {"Full Walk", "Theme-Only"}
        modes = data.get('Modes', [])
        if not isinstance(modes, list):
            result['issues'].append({
                'code': 'MODES_TYPE',
                'message': "Modes must be a list",
                'severity': 'blocking'
            })
        else:
            invalid_modes = set(modes) - allowed_modes
            if invalid_modes:
                result['issues'].append({
                    'code': 'MODES_VALUES',
                    'message': f"Invalid modes: {invalid_modes}",
                    'severity': 'blocking'
                })
    
    def validate_stones_slugs(self, data: Dict, result: Dict):
        """Validate stone slugs exist in registry."""
        stones = data.get('Stones', [])
        if not isinstance(stones, list):
            result['issues'].append({
                'code': 'STONES_TYPE',
                'message': "Stones must be a list",
                'severity': 'blocking'
            })
        else:
            for stone in stones:
                if isinstance(stone, dict) and 'slug' in stone:
                    slug = stone['slug'].strip().lower().replace(' ', '-')
                    if slug not in self.stones_slugs:
                        result['issues'].append({
                            'code': 'STONES_SLUG',
                            'message': f"Stone slug '{stone['slug']}' not in registry",
                            'severity': 'blocking'
                        })
    
    def validate_additional_properties(self, data: Dict, result: Dict):
        """Check for keys not allowed by schema."""
        if self.schema and 'properties' in self.schema:
            allowed_keys = set(self.schema['properties'].keys())
            additional_keys = set(data.keys()) - allowed_keys
            if additional_keys:
                result['issues'].append({
                    'code': 'EXTRA_KEYS',
                    'message': f"Additional properties not in schema: {additional_keys}",
                    'severity': 'fixable'
                })
    
    def validate_stable_ids(self, data: Dict, result: Dict, file_path: Path):
        """Validate Protocol ID based on mode."""
        protocol_id = data.get('Protocol ID', '')
        
        if self.args.id_mode == 'filename':
            expected_id = self.slugify(file_path.stem)
            if protocol_id != expected_id:
                result['issues'].append({
                    'code': 'ID_DERIVE',
                    'message': f"Protocol ID '{protocol_id}' should be '{expected_id}' from filename",
                    'severity': 'fixable'
                })
        elif protocol_id.startswith('auto_'):
            result['issues'].append({
                'code': 'ID_AUTO',
                'message': f"Auto-generated ID '{protocol_id}' detected",
                'severity': 'warning'
            })
    
    def validate_when_to_use(self, data: Dict, result: Dict):
        """Validate When To Use This Protocol field type."""
        when_to_use = data.get('When To Use This Protocol')
        
        # Check schema requirements for this field
        if self.schema and 'properties' in self.schema:
            when_to_use_schema = self.schema['properties'].get('When To Use This Protocol')
            if when_to_use_schema:
                expected_type = when_to_use_schema.get('type')
                if expected_type == 'string' and isinstance(when_to_use, list):
                    result['issues'].append({
                        'code': 'WHEN_TYPE',
                        'message': "When To Use This Protocol should be string, found array",
                        'severity': 'fixable'
                    })
                elif expected_type == 'array' and isinstance(when_to_use, str):
                    result['issues'].append({
                        'code': 'WHEN_TYPE',
                        'message': "When To Use This Protocol should be array, found string",
                        'severity': 'fixable'
                    })
    
    def apply_autofixes(self, data: Dict, result: Dict, file_path: Path):
        """Apply autofixes to the protocol data."""
        fixed = False
        
        # Fix SemVer
        if data.get('Version') == '1':
            data['Version'] = '1.0.0'
            result['fixed'].append("Version: '1' → '1.0.0'")
            fixed = True
        
        # Fix Created At
        created_at = data.get('Created At', '')
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', created_at):
            if self.args.date_mode == 'today':
                data['Created At'] = datetime.now().strftime('%Y-%m-%d')
                result['fixed'].append(f"Created At: '{created_at}' → '{data['Created At']}'")
                fixed = True
        
        # Fix Protocol ID
        if self.args.id_mode == 'filename':
            expected_id = self.slugify(file_path.stem)
            if data.get('Protocol ID') != expected_id:
                data['Protocol ID'] = expected_id
                result['fixed'].append(f"Protocol ID: '{data.get('Protocol ID', '')}' → '{expected_id}'")
                fixed = True
        
        # Fix stone slugs
        stones = data.get('Stones', [])
        if isinstance(stones, list):
            for stone in stones:
                if isinstance(stone, dict) and 'slug' in stone:
                    original_slug = stone['slug']
                    normalized_slug = original_slug.strip().lower().replace(' ', '-')
                    if normalized_slug != original_slug:
                        stone['slug'] = normalized_slug
                        result['fixed'].append(f"Stone slug: '{original_slug}' → '{normalized_slug}'")
                        fixed = True
        
        # Remove unknown keys
        if self.schema and 'properties' in self.schema:
            allowed_keys = set(self.schema['properties'].keys())
            keys_to_remove = set(data.keys()) - allowed_keys
            if keys_to_remove:
                for key in keys_to_remove:
                    del data[key]
                    result['fixed'].append(f"Removed unknown key: '{key}'")
                fixed = True
        
        # Fix When To Use type
        when_to_use = data.get('When To Use This Protocol')
        if self.schema and 'properties' in self.schema:
            when_to_use_schema = self.schema['properties'].get('When To Use This Protocol')
            if when_to_use_schema:
                expected_type = when_to_use_schema.get('type')
                if expected_type == 'string' and isinstance(when_to_use, list):
                    data['When To Use This Protocol'] = '; '.join(when_to_use)
                    result['fixed'].append("When To Use This Protocol: array → string")
                    fixed = True
                elif expected_type == 'array' and isinstance(when_to_use, str):
                    data['When To Use This Protocol'] = [when_to_use]
                    result['fixed'].append("When To Use This Protocol: string → array")
                    fixed = True
        
        # Sort arrays where order doesn't matter
        sortable_arrays = ['Tags', 'Related Protocols', 'Tone Markers', 'Fields', 'Bridges', 'Stones']
        for key in sortable_arrays:
            if key in data and isinstance(data[key], list):
                original = data[key].copy()
                data[key].sort()
                if data[key] != original:
                    result['fixed'].append(f"Sorted array: {key}")
                    fixed = True
        
        # Fix placeholders if possible
        placeholders = {
            "[Protocol Title]": file_path.stem.replace('_', ' ').title(),
            "[Short Title]": file_path.stem.replace('_', ' ').title(),
        }
        
        def fix_placeholders(obj, path=""):
            nonlocal fixed
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, str) and v in placeholders:
                        obj[k] = placeholders[v]
                        result['fixed'].append(f"Fixed placeholder '{v}' → '{placeholders[v]}' at {path}.{k}")
                        fixed = True
                    elif isinstance(v, (dict, list)):
                        fix_placeholders(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    if isinstance(v, str) and v in placeholders:
                        obj[i] = placeholders[v]
                        result['fixed'].append(f"Fixed placeholder '{v}' → '{placeholders[v]}' at {path}[{i}]")
                        fixed = True
                    elif isinstance(v, (dict, list)):
                        fix_placeholders(v, f"{path}[{i}]" if path else f"[{i}]")
        
        fix_placeholders(data)
        
        if fixed:
            result['status'] = 'fixed' if result['status'] == 'blocking' else 'fixed'
    
    def create_backup(self, file_path: Path) -> bool:
        """Create backup of file before modification."""
        if not self.args.backup_dir:
            return True
        
        backup_dir = Path(self.args.backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create backup with just the filename to avoid path issues
        backup_path = backup_dir / file_path.name
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            shutil.copy2(file_path, backup_path)
            return True
        except Exception as e:
            print(f"Warning: Failed to create backup for {file_path}: {e}")
            return False
    
    def write_file(self, file_path: Path, data: Dict) -> bool:
        """Atomically write file with proper formatting."""
        try:
            # Create temporary file in same directory
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.json.tmp',
                dir=file_path.parent,
                text=True
            )
            
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
                    f.write('\n')  # Ensure trailing newline
                
                # Atomic rename
                os.rename(temp_path, file_path)
                return True
            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            print(f"Error writing file {file_path}: {e}")
            return False
    
    def generate_diff_preview(self, original_data: Dict, new_data: Dict) -> List[str]:
        """Generate diff preview for changes."""
        # Simple diff by comparing JSON strings
        import difflib
        
        original_str = json.dumps(original_data, indent=2, sort_keys=True)
        new_str = json.dumps(new_data, indent=2, sort_keys=True)
        
        diff_lines = list(difflib.unified_diff(
            original_str.splitlines(keepends=True),
            new_str.splitlines(keepends=True),
            fromfile='original',
            tofile='modified',
            lineterm=''
        ))
        
        # Return first 10 lines of diff
        return [line.rstrip() for line in diff_lines[:10]]
    
    def process_files(self):
        """Process all protocol files with progress bar."""
        files = self.get_protocol_files()
        self.results['totals']['total_files'] = len(files)
        
        if not files:
            print("No protocol files found matching the glob pattern.")
            return
        
        print(f"Processing {len(files)} protocol files...")
        
        with ThreadPoolExecutor(max_workers=self.args.max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.process_single_file, file_path): file_path
                for file_path in files
            }
            
            # Process with progress bar
            with tqdm(total=len(files), desc="Processing files") as pbar:
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        file_result = future.result()
                        self.results['files'].append(file_result)
                        
                        # Update totals
                        status = file_result['status']
                        if status == 'valid':
                            self.results['totals']['valid'] += 1
                        elif status == 'fixed':
                            self.results['totals']['fixed'] += 1
                        elif status == 'flagged':
                            self.results['totals']['flagged'] += 1
                        elif status == 'blocking':
                            self.results['totals']['blocking'] += 1
                        
                        # Update error counts
                        for issue in file_result['issues']:
                            code = issue['code']
                            self.results['by_error'][code] = self.results['by_error'].get(code, 0) + 1
                        
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
                        self.results['files'].append({
                            'path': str(file_path),
                            'issues': [{'code': 'PROCESS_ERROR', 'message': str(e)}],
                            'fixed': [],
                            'diff_preview': [],
                            'status': 'blocking'
                        })
                        self.results['totals']['blocking'] += 1
                    
                    pbar.update(1)
    
    def process_single_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a single protocol file."""
        result = self.validate_protocol(file_path)
        
        # Apply fixes if requested and not dry run
        if self.args.fix and not self.args.dry_run and result['fixed']:
            # Create backup
            self.create_backup(file_path)
            
            # Load original data for diff
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_data = json.load(f)
            except Exception:
                original_data = {}
            
            # Reload and apply fixes
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Re-apply fixes
            self.apply_autofixes(data, result, file_path)
            
            # Generate diff preview
            result['diff_preview'] = self.generate_diff_preview(original_data, data)
            
            # Write file
            if not self.write_file(file_path, data):
                result['issues'].append({
                    'code': 'WRITE_ERROR',
                    'message': 'Failed to write fixed file',
                    'severity': 'blocking'
                })
        
        return result
    
    def print_summary(self):
        """Print console summary."""
        totals = self.results['totals']
        
        print("\n" + "="*60)
        print("PROTOCOL CLEANUP SUMMARY")
        print("="*60)
        
        print(f"Total files processed: {totals['total_files']}")
        print(f"✅ Valid: {totals['valid']}")
        print(f"🛠  Fixed: {totals['fixed']}")
        print(f"⚠️  Flagged: {totals['flagged']}")
        print(f"❌ Blocking: {totals['blocking']}")
        
        if self.results['by_error']:
            print(f"\nTop error types:")
            sorted_errors = sorted(self.results['by_error'].items(), key=lambda x: x[1], reverse=True)
            for code, count in sorted_errors[:10]:
                print(f"  {code}: {count}")
        
        # Final status line
        status_line = f"✅ Clean: {totals['valid']} | 🛠 Fixed: {totals['fixed']} | ⚠️ Flagged: {totals['flagged']} | ❌ Blocking: {totals['blocking']}"
        print(f"\n{status_line}")
    
    def save_report(self):
        """Save JSON report if requested."""
        if self.args.report:
            report_path = Path(self.args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            
            print(f"\nDetailed report saved to: {report_path}")
    
    def run(self) -> int:
        """Main execution method."""
        # Load required files
        if not self.load_schema():
            return 2
        if not self.load_template():
            return 2
        if not self.load_stones_registry():
            return 2
        
        # Process files
        self.process_files()
        
        # Print summary
        self.print_summary()
        
        # Save report
        self.save_report()
        
        # Determine exit code
        if self.args.strict and self.results['totals']['blocking'] > 0:
            return 1
        return 0


def create_self_test_protocols():
    """Create test protocols for self-test mode."""
    test_dir = Path(tempfile.mkdtemp())
    
    # Valid protocol
    valid_protocol = {
        "Protocol ID": "test-valid",
        "Title": "Test Valid Protocol",
        "Short Title": "Test Valid",
        "Description": "A valid test protocol",
        "Version": "1.0.0",
        "Created At": "2024-01-01",
        "Author": "Test Author",
        "Modes": ["Full Walk"],
        "Themes": ["Theme 1", "Theme 2", "Theme 3", "Theme 4", "Theme 5"],
        "Completion Prompts": ["Prompt 1", "Prompt 2"],
        "Stones": [{"slug": "light-before-form", "alignment": "high"}],
        "When To Use This Protocol": "Use when testing"
    }
    
    # Invalid protocol with issues
    invalid_protocol = {
        "Protocol ID": "auto_test_invalid",
        "Title": "[Protocol Title]",
        "Short Title": "[Short Title]",
        "Description": "A test protocol with issues",
        "Version": "1",
        "Created At": "invalid-date",
        "Author": "Test Author",
        "Modes": ["Invalid Mode"],
        "Themes": ["Only", "Two", "Themes"],
        "Completion Prompts": ["Only one prompt"],
        "Stones": [{"slug": "invalid-stone", "alignment": "high"}],
        "When To Use This Protocol": ["Should be string"],
        "Extra Key": "Should be removed"
    }
    
    # Write test files (only JSON files)
    (test_dir / "valid_protocol.json").write_text(json.dumps(valid_protocol, indent=2))
    (test_dir / "invalid_protocol.json").write_text(json.dumps(invalid_protocol, indent=2))
    
    return test_dir


def run_self_test():
    """Run self-test mode."""
    print("Running self-test...")
    
    # Create test protocols
    test_dir = create_self_test_protocols()
    
    try:
        # Create test stones file
        stones_file = test_dir / "test_stones.yaml"
        stones_content = """
stones:
  - slug: light-before-form
    name: Light Before Form
  - slug: speed-of-trust
    name: Speed of Trust
"""
        stones_file.write_text(stones_content)
        
        # Create minimal schema
        schema_file = test_dir / "test_schema.json"
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "Protocol ID": {"type": "string"},
                "Title": {"type": "string"},
                "Short Title": {"type": "string"},
                "Description": {"type": "string"},
                "Version": {"type": "string"},
                "Created At": {"type": "string"},
                "Author": {"type": "string"},
                "Modes": {"type": "array", "items": {"type": "string"}},
                "Themes": {"type": "array", "items": {"type": "string"}},
                "Completion Prompts": {"type": "array", "items": {"type": "string"}},
                "Stones": {"type": "array"},
                "When To Use This Protocol": {"type": "string"}
            },
            "required": ["Protocol ID", "Title", "Version", "Created At"]
        }
        schema_file.write_text(json.dumps(schema, indent=2))
        
        # Create minimal template
        template_file = test_dir / "test_template.json"
        template = {
            "Protocol ID": "[Protocol ID]",
            "Title": "[Protocol Title]",
            "Short Title": "[Short Title]"
        }
        template_file.write_text(json.dumps(template, indent=2))
        
        # Run cleaner (exclude schema and template files)
        args = argparse.Namespace(
            protocol_glob=str(test_dir / "*protocol*.json"),
            schema_path=str(schema_file),
            template_path=str(template_file),
            stones_path=str(stones_file),
            fix=True,
            strict=False,
            dry_run=False,
            backup_dir=None,
            max_workers=1,
            id_mode='filename',
            date_mode='today',
            report=None,
            exclude="*schema*.json,*template*.json"
        )
        
        cleaner = ProtocolCleaner(args)
        exit_code = cleaner.run()
        
        # Check results
        results = cleaner.results
        assert results['totals']['total_files'] == 2, f"Expected 2 files, got {results['totals']['total_files']}"
        assert results['totals']['fixed'] >= 1, f"Expected at least 1 fixed file, got {results['totals']['fixed']}"
        
        print("✅ Self-test passed!")
        return 0
        
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)


def print_pre_commit_hook():
    """Print pre-commit hook configuration."""
    hook_content = """# Protocol validation hook
repos:
  - repo: local
    hooks:
      - id: protocol-cleanup
        name: Protocol Cleanup (Report Only)
        entry: python3 scripts/clean_protocols.py
        args: [
          "--protocol-glob", "protocols/*.json",
          "--schema-path", "protocol_template_schema_v1.json",
          "--template-path", "protocol_template_locked_v1.json", 
          "--stones-path", "Foundation_Stones_of_the_System.txt",
          "--strict"
        ]
        language: system
        files: \\.json$
"""
    print("Add this to your .pre-commit-config.yaml:")
    print(hook_content)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Protocol cleanup and validation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Special modes (check these first)
    parser.add_argument('--self-test', action='store_true',
                       help='Run self-test with sample protocols')
    parser.add_argument('--print-pre-commit', action='store_true',
                       help='Print pre-commit hook configuration')
    
    # Required arguments (only required if not in special mode)
    parser.add_argument('--protocol-glob',
                       help='Glob pattern for protocol JSON files')
    parser.add_argument('--schema-path',
                       help='Path to protocol schema JSON file')
    parser.add_argument('--template-path',
                       help='Path to locked template JSON file')
    parser.add_argument('--stones-path',
                       help='Path to Foundation Stones registry file')
    
    # Mode flags
    parser.add_argument('--fix', action='store_true',
                       help='Apply safe autofixes')
    parser.add_argument('--strict', action='store_true',
                       help='Exit non-zero if blocking errors remain')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show proposed diffs but do not write files')
    
    # Configuration
    parser.add_argument('--backup-dir', default='.backups',
                       help='Directory for file backups (default: .backups)')
    parser.add_argument('--max-workers', type=int, default=8,
                       help='Maximum worker threads (default: 8)')
    parser.add_argument('--id-mode', choices=['filename', 'preserve'], default='preserve',
                       help='Protocol ID generation mode (default: preserve)')
    parser.add_argument('--date-mode', choices=['preserve', 'today'], default='preserve',
                       help='Created At date mode (default: preserve)')
    
    # Output
    parser.add_argument('--report', help='Path for JSON report output')
    parser.add_argument('--exclude', help='Comma-separated glob patterns to exclude')
    
    args = parser.parse_args()
    
    # Handle special modes first
    if args.self_test:
        return run_self_test()
    
    if args.print_pre_commit:
        print_pre_commit_hook()
        return 0
    
    # Check required arguments for main mode
    required_args = ['protocol_glob', 'schema_path', 'template_path', 'stones_path']
    missing_args = [arg for arg in required_args if not getattr(args, arg)]
    if missing_args:
        parser.error(f"the following arguments are required: {', '.join('--' + arg.replace('_', '-') for arg in missing_args)}")
    
    # Run main cleaner
    cleaner = ProtocolCleaner(args)
    return cleaner.run()


if __name__ == '__main__':
    sys.exit(main())
