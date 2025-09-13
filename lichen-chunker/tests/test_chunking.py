"""Tests for chunking functionality."""

import tempfile
from pathlib import Path

import pytest

from lichen_chunker.chunking import ProtocolChunker
from lichen_chunker.types import Protocol, OverallOutcomes, Theme, ThemeOutcomes, OutcomeLevel


def create_test_protocol() -> Protocol:
    """Create a test protocol for testing."""
    return Protocol(
        title="Test Protocol",
        short_title="Test",
        overall_purpose="Test purpose",
        why_matters="Test importance",
        when_to_use="Test usage",
        overall_outcomes=OverallOutcomes(
            **{
                "Poor": "Poor outcome",
                "Expected": "Expected outcome", 
                "Excellent": "Excellent outcome",
                "Transcendent": "Transcendent outcome"
            }
        ),
        themes=[
                Theme(
                    **{
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
                )
        ],
        **{
            "Completion Prompts": ["Prompt 1", "Prompt 2"]
        }
    )


def test_chunker_initialization():
    """Test chunker initialization."""
    chunker = ProtocolChunker(max_tokens=500, overlap_tokens=50)
    assert chunker.max_tokens == 500
    assert chunker.overlap_tokens == 50


def test_count_tokens():
    """Test token counting."""
    chunker = ProtocolChunker()
    
    # Test with tiktoken if available
    if chunker.encoding:
        count = chunker.count_tokens("Hello world")
        assert count > 0
    else:
        # Test fallback
        count = chunker.count_tokens("Hello world")
        assert count > 0


def test_chunk_protocol():
    """Test protocol chunking."""
    chunker = ProtocolChunker(max_tokens=100, overlap_tokens=10)
    protocol = create_test_protocol()
    source_path = Path("test.json")
    
    chunks = chunker.chunk_protocol(protocol, source_path, "test_protocol")
    
    assert len(chunks) > 0
    
    # Check chunk structure
    for chunk in chunks:
        assert chunk.text
        assert chunk.metadata.chunk_id
        assert chunk.metadata.protocol_id == "test_protocol"
        assert chunk.metadata.title == "Test Protocol"
        assert chunk.metadata.n_tokens > 0
        assert chunk.metadata.hash


def test_chunk_section():
    """Test section chunking."""
    chunker = ProtocolChunker(max_tokens=50, overlap_tokens=5)
    
    # Create a long section that needs chunking
    long_content = "This is a test sentence. " * 20  # Make it long enough to chunk
    
    chunks = chunker._chunk_section(
        content=long_content,
        protocol_id="test",
        title="Test Protocol",
        section_name="Test Section",
        section_idx=0,
        source_path=Path("test.json"),
        stones=[]
    )
    
    assert len(chunks) > 1  # Should be chunked into multiple pieces
    
    # Check that chunks have proper IDs
    for i, chunk in enumerate(chunks):
        assert chunk.metadata.chunk_id == f"test::s0::c{i}"
        assert chunk.metadata.section_name == "Test Section"
        assert chunk.metadata.section_idx == 0
        assert chunk.metadata.chunk_idx == i


def test_get_sections():
    """Test section extraction."""
    chunker = ProtocolChunker()
    protocol = create_test_protocol()
    
    sections = chunker._get_sections(protocol)
    
    assert len(sections) > 0
    
    # Check that we have expected sections
    section_names = [name for name, _ in sections]
    assert "Title" in section_names
    assert "Overall Purpose" in section_names
    assert "Themes" in section_names or any("Theme" in name for name in section_names)
    assert "Completion Prompts" in section_names


def test_format_theme():
    """Test theme formatting."""
    chunker = ProtocolChunker()
    protocol = create_test_protocol()
    theme = protocol.themes[0]
    
    formatted = chunker._format_theme(theme)
    
    assert "Test Theme" in formatted
    assert "Test theme purpose" in formatted
    assert "Poor pattern" in formatted
    assert "Question 1" in formatted
    assert "Question 2" in formatted
