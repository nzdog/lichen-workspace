"""
Redaction module for removing sensitive information from logs and data.

Provides regex patterns and functions to redact emails, phone numbers, names,
and other sensitive data before writing to logs or other outputs.
"""

import re
import os
from typing import Dict, Any, List, Union
from dataclasses import dataclass


@dataclass
class RedactionPattern:
    """A redaction pattern with name, regex, and replacement."""
    name: str
    pattern: re.Pattern
    replacement: str
    description: str


class Redactor:
    """Redacts sensitive information from text and data structures."""
    
    def __init__(self):
        """Initialize redaction patterns."""
        self.patterns = self._create_patterns()
        # Default to enabled (1), only disable if explicitly set to "0"
        redact_logs = os.getenv("REDACT_LOGS", "1").strip().lower()
        self.redaction_enabled = redact_logs != "0"
    
    def _create_patterns(self) -> List[RedactionPattern]:
        """Create regex patterns for redaction."""
        patterns = []
        
        # Email addresses
        patterns.append(RedactionPattern(
            name="email",
            pattern=re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            replacement="[EMAIL_REDACTED]",
            description="Email addresses"
        ))
        
        # Phone numbers (precise patterns to avoid false positives)
        # US phone with parentheses (most reliable)
        patterns.append(RedactionPattern(
            name="phone_us_parens",
            pattern=re.compile(r'\([0-9]{3}\)\s*[0-9]{3}[-.\s]?[0-9]{4}\b'),
            replacement="[PHONE_REDACTED]",
            description="US phone numbers with parentheses"
        ))
        
        # US phone with dashes (3-3-4 format)
        patterns.append(RedactionPattern(
            name="phone_us_dashes",
            pattern=re.compile(r'\b[0-9]{3}-[0-9]{3}-[0-9]{4}\b'),
            replacement="[PHONE_REDACTED]",
            description="US phone numbers with dashes"
        ))
        
        # US phone with dots (3.3.4 format)
        patterns.append(RedactionPattern(
            name="phone_us_dots",
            pattern=re.compile(r'\b[0-9]{3}\.[0-9]{3}\.[0-9]{4}\b'),
            replacement="[PHONE_REDACTED]",
            description="US phone numbers with dots"
        ))
        
        # US phone with spaces (3 3 4 format)
        patterns.append(RedactionPattern(
            name="phone_us_spaces",
            pattern=re.compile(r'\b[0-9]{3}\s[0-9]{3}\s[0-9]{4}\b'),
            replacement="[PHONE_REDACTED]",
            description="US phone numbers with spaces"
        ))
        
        # International phone with + prefix
        patterns.append(RedactionPattern(
            name="phone_international",
            pattern=re.compile(r'\+[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}\b'),
            replacement="[PHONE_REDACTED]",
            description="International phone numbers"
        ))
        
        # Credit card numbers (basic pattern)
        patterns.append(RedactionPattern(
            name="credit_card",
            pattern=re.compile(r'\b[0-9]{4}[-.\s]?[0-9]{4}[-.\s]?[0-9]{4}[-.\s]?[0-9]{4}\b'),
            replacement="[CARD_REDACTED]",
            description="Credit card numbers"
        ))
        
        # SSN (US format) - more specific to avoid false positives
        patterns.append(RedactionPattern(
            name="ssn",
            pattern=re.compile(r'\b(?!000|666|9[0-9]{2})[0-9]{3}[-.\s]?(?!00)[0-9]{2}[-.\s]?(?!0000)[0-9]{4}\b'),
            replacement="[SSN_REDACTED]",
            description="Social Security Numbers"
        ))
        
        # Common name patterns (basic)
        patterns.append(RedactionPattern(
            name="name_basic",
            pattern=re.compile(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'),
            replacement="[NAME_REDACTED]",
            description="Basic name patterns"
        ))
        
        # API keys and tokens
        patterns.append(RedactionPattern(
            name="api_key",
            pattern=re.compile(r'\b[A-Za-z0-9]{20,}\b'),
            replacement="[API_KEY_REDACTED]",
            description="API keys and tokens"
        ))
        
        # URLs with potential sensitive data
        patterns.append(RedactionPattern(
            name="url_sensitive",
            pattern=re.compile(r'https?://[^\s]+'),
            replacement="[URL_REDACTED]",
            description="URLs"
        ))
        
        return patterns
    
    def redact_text(self, text: str) -> str:
        """Redact sensitive information from text."""
        if not self.redaction_enabled or not text:
            return text
        
        redacted = text
        for pattern in self.patterns:
            redacted = pattern.pattern.sub(pattern.replacement, redacted)
        
        return redacted
    
    def redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact sensitive information from a dictionary."""
        if not self.redaction_enabled:
            return data
        
        redacted = {}
        for key, value in data.items():
            if isinstance(value, str):
                redacted[key] = self.redact_text(value)
            elif isinstance(value, dict):
                redacted[key] = self.redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = self.redact_list(value)
            else:
                redacted[key] = value
        
        return redacted
    
    def redact_list(self, data: List[Any]) -> List[Any]:
        """Recursively redact sensitive information from a list."""
        if not self.redaction_enabled:
            return data
        
        redacted = []
        for item in data:
            if isinstance(item, str):
                redacted.append(self.redact_text(item))
            elif isinstance(item, dict):
                redacted.append(self.redact_dict(item))
            elif isinstance(item, list):
                redacted.append(self.redact_list(item))
            else:
                redacted.append(item)
        
        return redacted
    
    def redact_jsonl_line(self, line: str) -> str:
        """Redact sensitive information from a JSONL line."""
        if not self.redaction_enabled or not line.strip():
            return line
        
        try:
            import json
            data = json.loads(line)
            redacted_data = self.redact_dict(data)
            return json.dumps(redacted_data) + '\n'
        except (json.JSONDecodeError, TypeError):
            # If it's not valid JSON, just redact as text
            return self.redact_text(line)
    
    def get_redaction_stats(self) -> Dict[str, Any]:
        """Get statistics about redaction patterns."""
        return {
            "enabled": self.redaction_enabled,
            "patterns_count": len(self.patterns),
            "patterns": [
                {
                    "name": p.name,
                    "description": p.description,
                    "replacement": p.replacement
                }
                for p in self.patterns
            ]
        }


# Global redactor instance
_redactor = None


def get_redactor() -> Redactor:
    """Get the global redactor instance."""
    global _redactor
    # Always create a new instance to respect environment changes
    _redactor = Redactor()
    return _redactor


def redact_text(text: str) -> str:
    """Convenience function to redact text."""
    return get_redactor().redact_text(text)


def redact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to redact dictionary."""
    return get_redactor().redact_dict(data)


def redact_jsonl_line(line: str) -> str:
    """Convenience function to redact JSONL line."""
    return get_redactor().redact_jsonl_line(line)
