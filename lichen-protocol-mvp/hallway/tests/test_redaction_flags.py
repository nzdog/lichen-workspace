"""
Test redaction environment flags and behavior.

Ensures REDACT_LOGS=1 masks sensitive tokens and REDACT_LOGS=0 preserves raw data.
"""

import os
import pytest
import sys
from pathlib import Path

# Add hallway directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from redaction import get_redactor, redact_text, redact_dict


class TestRedactionFlags:
    """Test redaction environment flag behavior."""
    
    def test_redaction_enabled_masks_tokens(self):
        """Test that REDACT_LOGS=1 masks sensitive tokens."""
        # Set redaction enabled
        os.environ["REDACT_LOGS"] = "1"
        
        # Get fresh redactor instance
        redactor = get_redactor()
        assert redactor.redaction_enabled, "Redaction should be enabled"
        
        # Test email redaction
        original = "Contact john@example.com for details"
        redacted = redact_text(original)
        assert "[EMAIL_REDACTED]" in redacted, "Email should be redacted"
        assert "john@example.com" not in redacted, "Original email should not appear"
        
        # Test phone redaction
        original = "Call (555) 123-4567 for support"
        redacted = redact_text(original)
        assert "[PHONE_REDACTED]" in redacted, "Phone should be redacted"
        assert "(555) 123-4567" not in redacted, "Original phone should not appear"
        
        # Test name redaction
        original = "John Smith is the contact person"
        redacted = redact_text(original)
        assert "[NAME_REDACTED]" in redacted, "Name should be redacted"
        assert "John Smith" not in redacted, "Original name should not appear"
        
        # Test API key redaction
        original = "Use API key sk-1234567890abcdef1234567890abcdef"
        redacted = redact_text(original)
        assert "[API_KEY_REDACTED]" in redacted, "API key should be redacted"
        assert "sk-1234567890abcdef1234567890abcdef" not in redacted, "Original API key should not appear"
    
    def test_redaction_disabled_preserves_raw(self):
        """Test that REDACT_LOGS=0 preserves raw data."""
        # Set redaction disabled
        os.environ["REDACT_LOGS"] = "0"
        
        # Get fresh redactor instance
        redactor = get_redactor()
        assert not redactor.redaction_enabled, "Redaction should be disabled"
        
        # Test email preservation
        original = "Contact john@example.com for details"
        redacted = redact_text(original)
        assert original == redacted, "Text should be unchanged when redaction disabled"
        assert "john@example.com" in redacted, "Original email should be preserved"
        
        # Test phone preservation
        original = "Call (555) 123-4567 for support"
        redacted = redact_text(original)
        assert original == redacted, "Text should be unchanged when redaction disabled"
        assert "(555) 123-4567" in redacted, "Original phone should be preserved"
        
        # Test name preservation
        original = "John Smith is the contact person"
        redacted = redact_text(original)
        assert original == redacted, "Text should be unchanged when redaction disabled"
        assert "John Smith" in redacted, "Original name should be preserved"
        
        # Test API key preservation
        original = "Use API key sk-1234567890abcdef1234567890abcdef"
        redacted = redact_text(original)
        assert original == redacted, "Text should be unchanged when redaction disabled"
        assert "sk-1234567890abcdef1234567890abcdef" in redacted, "Original API key should be preserved"
    
    def test_redaction_dict_behavior(self):
        """Test redaction behavior with dictionaries."""
        test_data = {
            "user_email": "john@example.com",
            "phone": "(555) 123-4567",
            "name": "John Smith",
            "api_key": "sk-1234567890abcdef1234567890abcdef",
            "normal_field": "This is normal text"
        }
        
        # Test with redaction enabled
        os.environ["REDACT_LOGS"] = "1"
        redacted_enabled = redact_dict(test_data)
        
        assert "[EMAIL_REDACTED]" in redacted_enabled["user_email"]
        assert "[PHONE_REDACTED]" in redacted_enabled["phone"]
        assert "[NAME_REDACTED]" in redacted_enabled["name"]
        assert "[API_KEY_REDACTED]" in redacted_enabled["api_key"]
        assert redacted_enabled["normal_field"] == "This is normal text"
        
        # Test with redaction disabled
        os.environ["REDACT_LOGS"] = "0"
        redacted_disabled = redact_dict(test_data)
        
        assert redacted_disabled == test_data, "Dictionary should be unchanged when redaction disabled"
    
    def test_redaction_stats(self):
        """Test redaction statistics reporting."""
        os.environ["REDACT_LOGS"] = "1"
        redactor = get_redactor()
        
        stats = redactor.get_redaction_stats()
        
        assert stats["enabled"] is True
        assert stats["patterns_count"] > 0
        assert "patterns" in stats
        assert len(stats["patterns"]) == stats["patterns_count"]
        
        # Check that patterns have required fields
        for pattern in stats["patterns"]:
            assert "name" in pattern
            assert "description" in pattern
            assert "replacement" in pattern
    
    def test_environment_flag_edge_cases(self):
        """Test edge cases for environment flag handling."""
        # Test invalid values (should default to enabled)
        os.environ["REDACT_LOGS"] = "invalid"
        redactor = get_redactor()
        assert redactor.redaction_enabled, "Invalid values should default to enabled"
        
        # Test empty value (should default to enabled)
        os.environ["REDACT_LOGS"] = ""
        redactor = get_redactor()
        assert redactor.redaction_enabled, "Empty values should default to enabled"
        
        # Test case sensitivity
        os.environ["REDACT_LOGS"] = "TRUE"
        redactor = get_redactor()
        assert redactor.redaction_enabled, "Case insensitive comparison should work"
        
        # Test whitespace
        os.environ["REDACT_LOGS"] = " 1 "
        redactor = get_redactor()
        assert redactor.redaction_enabled, "Whitespace should be handled correctly"
    
    def test_multiple_redaction_patterns(self):
        """Test that multiple patterns work together."""
        os.environ["REDACT_LOGS"] = "1"
        
        # Text with multiple sensitive patterns
        original = "Contact John Smith at john@example.com or call (555) 123-4567. Use API key sk-1234567890abcdef1234567890abcdef"
        redacted = redact_text(original)
        
        # All patterns should be redacted
        assert "[NAME_REDACTED]" in redacted
        assert "[EMAIL_REDACTED]" in redacted
        assert "[PHONE_REDACTED]" in redacted
        assert "[API_KEY_REDACTED]" in redacted
        
        # Original sensitive data should not appear
        assert "John Smith" not in redacted
        assert "john@example.com" not in redacted
        assert "(555) 123-4567" not in redacted
        assert "sk-1234567890abcdef1234567890abcdef" not in redacted


if __name__ == "__main__":
    pytest.main([__file__])
