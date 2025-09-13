"""Tests for schema validation."""

import json
import tempfile
from pathlib import Path

import pytest

from lichen_chunker.schema_validation import (
    validate_protocol_json,
    validate_protocol_file,
    normalize_protocol_data
)


def test_validate_protocol_json_valid():
    """Test validation of valid protocol JSON."""
    valid_protocol = {
        "Title": "Test Protocol",
        "Short Title": "Test",
        "Overall Purpose": "Test purpose",
        "Why This Matters": "Test importance",
        "When To Use This Protocol": "Test usage",
        "Overall Outcomes": {
            "Poor": "Poor outcome",
            "Expected": "Expected outcome",
            "Excellent": "Excellent outcome",
            "Transcendent": "Transcendent outcome"
        },
        "Themes": [
            {
                "Name": "Test Theme",
                "Purpose of This Theme": "Test theme purpose",
                "Why This Matters": "Test theme importance",
                "Outcomes": {
                    "Poor": {
                        "Present pattern": "Poor pattern",
                        "Immediate cost": "Poor cost",
                        "30-90 day system effect": "Poor effect",
                        "Signals": "Poor signals",
                        "Edge condition": "Poor edge",
                        "Example moves": "Poor moves",
                        "Future effect": "Poor future"
                    },
                    "Expected": {
                        "Present pattern": "Expected pattern",
                        "Immediate cost": "Expected cost",
                        "30-90 day system effect": "Expected effect",
                        "Signals": "Expected signals",
                        "Edge condition": "Expected edge",
                        "Example moves": "Expected moves",
                        "Future effect": "Expected future"
                    },
                    "Excellent": {
                        "Present pattern": "Excellent pattern",
                        "Immediate cost": "Excellent cost",
                        "30-90 day system effect": "Excellent effect",
                        "Signals": "Excellent signals",
                        "Edge condition": "Excellent edge",
                        "Example moves": "Excellent moves",
                        "Future effect": "Excellent future"
                    },
                    "Transcendent": {
                        "Present pattern": "Transcendent pattern",
                        "Immediate cost": "Transcendent cost",
                        "30-90 day system effect": "Transcendent effect",
                        "Signals": "Transcendent signals",
                        "Edge condition": "Transcendent edge",
                        "Example moves": "Transcendent moves",
                        "Future effect": "Transcendent future"
                    }
                },
                "Guiding Questions": ["Question 1", "Question 2"]
            }
        ],
        "Completion Prompts": ["Prompt 1", "Prompt 2"]
    }
    
    is_valid, errors = validate_protocol_json(valid_protocol)
    assert is_valid
    assert len(errors) == 0


def test_validate_protocol_json_invalid():
    """Test validation of invalid protocol JSON."""
    invalid_protocol = {
        "Title": "Test Protocol",
        # Missing required fields
    }
    
    is_valid, errors = validate_protocol_json(invalid_protocol)
    assert not is_valid
    assert len(errors) > 0


def test_validate_protocol_file():
    """Test validation of protocol file."""
    valid_protocol = {
        "Title": "Test Protocol",
        "Short Title": "Test",
        "Overall Purpose": "Test purpose",
        "Why This Matters": "Test importance",
        "When To Use This Protocol": "Test usage",
        "Overall Outcomes": {
            "Poor": "Poor outcome",
            "Expected": "Expected outcome",
            "Excellent": "Excellent outcome",
            "Transcendent": "Transcendent outcome"
        },
            "Themes": [
                {
                    "Name": "Test Theme",
                    "Purpose of This Theme": "Test purpose",
                    "Why This Matters": "Test importance",
                    "Outcomes": {
                        "Poor": {
                            "Present pattern": "Poor pattern",
                            "Immediate cost": "Poor cost",
                            "30-90 day system effect": "Poor effect",
                            "Signals": "Poor signals",
                            "Edge condition": "Poor edge",
                            "Example moves": "Poor moves",
                            "Future effect": "Poor future"
                        },
                        "Expected": {
                            "Present pattern": "Expected pattern",
                            "Immediate cost": "Expected cost",
                            "30-90 day system effect": "Expected effect",
                            "Signals": "Expected signals",
                            "Edge condition": "Expected edge",
                            "Example moves": "Expected moves",
                            "Future effect": "Expected future"
                        },
                        "Excellent": {
                            "Present pattern": "Excellent pattern",
                            "Immediate cost": "Excellent cost",
                            "30-90 day system effect": "Excellent effect",
                            "Signals": "Excellent signals",
                            "Edge condition": "Excellent edge",
                            "Example moves": "Excellent moves",
                            "Future effect": "Excellent future"
                        },
                        "Transcendent": {
                            "Present pattern": "Transcendent pattern",
                            "Immediate cost": "Transcendent cost",
                            "30-90 day system effect": "Transcendent effect",
                            "Signals": "Transcendent signals",
                            "Edge condition": "Transcendent edge",
                            "Example moves": "Transcendent moves",
                            "Future effect": "Transcendent future"
                        }
                    },
                    "Guiding Questions": ["Question 1"]
                }
            ],
        "Completion Prompts": ["Prompt 1"]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
        json.dump(valid_protocol, tmp_file)
        tmp_path = Path(tmp_file.name)
    
    try:
        is_valid, errors, data = validate_protocol_file(tmp_path)
        assert is_valid
        assert len(errors) == 0
        assert data is not None
    finally:
        tmp_path.unlink(missing_ok=True)


def test_normalize_protocol_data():
    """Test protocol data normalization."""
    protocol_data = {
        "Completion Prompts": "Single prompt",  # Should become array
        "Themes": [
            {
                "Guiding Questions": "Single question"  # Should become array
            }
        ]
    }
    
    normalized = normalize_protocol_data(protocol_data)
    
    assert isinstance(normalized["Completion Prompts"], list)
    assert normalized["Completion Prompts"] == ["Single prompt"]
    assert isinstance(normalized["Themes"][0]["Guiding Questions"], list)
    assert normalized["Themes"][0]["Guiding Questions"] == ["Single question"]
