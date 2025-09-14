#!/usr/bin/env python3
"""
Block vector and index artifacts from being committed.

This script checks staged files against a list of blocked patterns
and exits with non-zero status if any violations are found.
"""

import sys
import subprocess
from pathlib import Path
from fnmatch import fnmatch


# Patterns to block from being committed
BLOCKED_PATTERNS = [
    "lichen-chunker/index/**",
    "lichen-chunker/cache/**", 
    "vector_store/**",
    "indexes/**",
    "**/*.faiss",
    "**/*.log",
    "data/**",
    "artifacts/**",
    "storage/**"
]


def get_staged_files():
    """Get list of staged files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError as e:
        print(f"Error getting staged files: {e}", file=sys.stderr)
        return []
    except FileNotFoundError:
        print("Error: git command not found", file=sys.stderr)
        return []


def check_file_against_patterns(file_path):
    """Check if a file path matches any blocked pattern."""
    for pattern in BLOCKED_PATTERNS:
        if fnmatch(file_path, pattern):
            return True
    return False


def main():
    """Main function to check staged files against blocked patterns."""
    staged_files = get_staged_files()
    
    if not staged_files:
        # No staged files, nothing to check
        sys.exit(0)
    
    violations = []
    for file_path in staged_files:
        if check_file_against_patterns(file_path):
            violations.append(file_path)
    
    if violations:
        print("Error: The following files are blocked from being committed:", file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        print("\nThese files contain vector data, indexes, or artifacts that should not be committed.", file=sys.stderr)
        print("Please remove them from staging or add them to .gitignore.", file=sys.stderr)
        sys.exit(1)
    
    # No violations found
    sys.exit(0)


if __name__ == "__main__":
    main()
