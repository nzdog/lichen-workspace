"""
Test phone pattern precision to ensure common numeric IDs are not flagged as phones.

Ensures timestamps, story IDs, and other legitimate numeric sequences are not
incorrectly redacted as phone numbers.
"""

import os
import pytest
import sys
from pathlib import Path

# Add hallway directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from redaction import get_redactor, redact_text


class TestPhonePatternPrecision:
    """Test phone pattern precision to avoid false positives."""
    
    def setup_method(self):
        """Set up test environment."""
        os.environ["REDACT_LOGS"] = "1"
        self.redactor = get_redactor()
    
    def test_timestamps_not_redacted(self):
        """Test that timestamps are not redacted as phone numbers."""
        test_cases = [
            "2025-09-12T17:30:00Z",
            "2025-09-12 17:30:00",
            "1757654783.5098612",  # Unix timestamp
            "2025-09-12",
            "17:30:00",
            "2025-09-12T17:30:00.123456Z",
            "2025-09-12T17:30:00+00:00",
        ]
        
        for timestamp in test_cases:
            redacted = redact_text(timestamp)
            assert timestamp == redacted, f"Timestamp '{timestamp}' should not be redacted"
            assert "[PHONE_REDACTED]" not in redacted, f"Timestamp '{timestamp}' should not be flagged as phone"
    
    def test_story_ids_not_redacted(self):
        """Test that story IDs and similar numeric identifiers are not redacted."""
        test_cases = [
            "Story ID: 1234567890",
            "Document ID: 9876543210",
            "Reference: 555-1234-5678",  # This might look like phone but is actually an ID
            "Case number: 123-45-6789",  # This might look like SSN but is actually a case ID
            "Order ID: 1234567890123456",
            "Transaction: 1234567890",
            "Version: 1.2.3.4",
            "Build: 2025.09.12.1730",
        ]
        
        for test_case in test_cases:
            redacted = redact_text(test_case)
            # These should not be redacted as they are not in phone format
            assert "[PHONE_REDACTED]" not in redacted, f"ID '{test_case}' should not be flagged as phone"
    
    def test_legitimate_phone_numbers_redacted(self):
        """Test that legitimate phone numbers are still redacted."""
        test_cases = [
            "(555) 123-4567",
            "555-123-4567",
            "555.123.4567",
            "555 123 4567",
            "+1-555-123-4567",
            "+1 (555) 123-4567",
            "+1.555.123.4567",
            "+1 555 123 4567",
            "1-555-123-4567",
            "1 (555) 123-4567",
            "1.555.123.4567",
            "1 555 123 4567",
        ]
        
        for phone in test_cases:
            redacted = redact_text(phone)
            assert "[PHONE_REDACTED]" in redacted, f"Phone '{phone}' should be redacted"
            assert phone not in redacted, f"Original phone '{phone}' should not appear in redacted text"
    
    def test_mixed_content_precision(self):
        """Test precision with mixed content containing both phones and non-phones."""
        test_cases = [
            {
                "text": "Call (555) 123-4567 or visit story ID 1234567890",
                "should_redact": ["(555) 123-4567"],
                "should_preserve": ["1234567890"]
            },
            {
                "text": "Contact at 555-123-4567, timestamp: 2025-09-12T17:30:00Z",
                "should_redact": ["555-123-4567"],
                "should_preserve": ["2025-09-12T17:30:00Z"]
            },
            {
                "text": "Phone: +1-555-123-4567, Document: 9876543210",
                "should_redact": ["+1-555-123-4567"],
                "should_preserve": ["9876543210"]
            },
            {
                "text": "Order 1234567890 placed at 17:30:00, call (555) 123-4567",
                "should_redact": ["(555) 123-4567"],
                "should_preserve": ["1234567890", "17:30:00"]
            }
        ]
        
        for test_case in test_cases:
            text = test_case["text"]
            redacted = redact_text(text)
            
            # Check that phones are redacted
            for phone in test_case["should_redact"]:
                assert "[PHONE_REDACTED]" in redacted, f"Phone '{phone}' should be redacted in '{text}'"
                assert phone not in redacted, f"Original phone '{phone}' should not appear in redacted text"
            
            # Check that non-phones are preserved
            for preserve in test_case["should_preserve"]:
                assert preserve in redacted, f"Non-phone '{preserve}' should be preserved in '{text}'"
    
    def test_edge_case_formats(self):
        """Test edge cases that might be ambiguous."""
        test_cases = [
            # These should NOT be redacted (not phone format)
            "1234567890",  # Just 10 digits, no formatting
            
            # These SHOULD be redacted (phone format)
            "(123) 456-7890",  # Proper phone format
            "123-456-7890",  # Standard phone format
            "123.456.7890",  # Phone with dots
            "+1-123-456-7890",  # International format
            
            # These SHOULD be redacted (SSN format)
            "123-45-6789",  # SSN format with dashes
            "123.45.6789",  # SSN format with dots
            "123 45 6789",  # SSN format with spaces
        ]
        
        for test_case in test_cases:
            redacted = redact_text(test_case)
            
            if test_case in ["(123) 456-7890", "123-456-7890", "123.456.7890", "+1-123-456-7890"]:
                # These should be redacted as phones
                assert "[PHONE_REDACTED]" in redacted, f"'{test_case}' should be redacted as phone"
                assert test_case not in redacted, f"Original '{test_case}' should not appear"
            elif test_case in ["123-45-6789", "123.45.6789", "123 45 6789"]:
                # These should be redacted as SSN
                assert "[SSN_REDACTED]" in redacted, f"'{test_case}' should be redacted as SSN"
                assert test_case not in redacted, f"Original '{test_case}' should not appear"
            else:
                # These should not be redacted
                assert test_case == redacted, f"'{test_case}' should not be redacted"
                assert "[PHONE_REDACTED]" not in redacted, f"'{test_case}' should not be flagged as phone"
    
    def test_ssn_vs_phone_distinction(self):
        """Test that SSNs and phones are handled differently."""
        test_cases = [
            {
                "text": "SSN: 123-45-6789",
                "expected_redaction": "[SSN_REDACTED]",
                "should_not_contain": "[PHONE_REDACTED]"
            },
            {
                "text": "Phone: (123) 456-7890",
                "expected_redaction": "[PHONE_REDACTED]",
                "should_not_contain": "[SSN_REDACTED]"
            }
        ]
        
        for test_case in test_cases:
            redacted = redact_text(test_case["text"])
            assert test_case["expected_redaction"] in redacted, f"Expected redaction for '{test_case['text']}'"
            assert test_case["should_not_contain"] not in redacted, f"Should not contain wrong redaction for '{test_case['text']}'"
    
    def test_credit_card_vs_phone_distinction(self):
        """Test that credit cards and phones are handled differently."""
        test_cases = [
            {
                "text": "Card: 4532-1234-5678-9012",
                "expected_redaction": "[CARD_REDACTED]",
                "should_not_contain": "[PHONE_REDACTED]"
            },
            {
                "text": "Phone: (555) 123-4567",
                "expected_redaction": "[PHONE_REDACTED]",
                "should_not_contain": "[CARD_REDACTED]"
            }
        ]
        
        for test_case in test_cases:
            redacted = redact_text(test_case["text"])
            assert test_case["expected_redaction"] in redacted, f"Expected redaction for '{test_case['text']}'"
            assert test_case["should_not_contain"] not in redacted, f"Should not contain wrong redaction for '{test_case['text']}'"


if __name__ == "__main__":
    pytest.main([__file__])
