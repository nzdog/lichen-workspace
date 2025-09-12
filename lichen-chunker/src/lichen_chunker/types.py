"""Pydantic models for Lichen Protocol data structures."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class OutcomeLevel(BaseModel):
    """Represents a single outcome level (Poor, Expected, Excellent, Transcendent)."""
    present_pattern: str = Field(alias="Present pattern")
    immediate_cost: str = Field(alias="Immediate cost")
    system_effect_30_90: str = Field(alias="30-90 day system effect")
    signals: str = Field(alias="Signals")
    edge_condition: str = Field(alias="Edge condition")
    example_moves: str = Field(alias="Example moves")
    future_effect: str = Field(alias="Future effect")

    class Config:
        populate_by_name = True


class ThemeOutcomes(BaseModel):
    """Outcomes for a theme across all levels."""
    poor: OutcomeLevel = Field(alias="Poor")
    expected: OutcomeLevel = Field(alias="Expected")
    excellent: OutcomeLevel = Field(alias="Excellent")
    transcendent: OutcomeLevel = Field(alias="Transcendent")

    class Config:
        populate_by_name = True


class Theme(BaseModel):
    """A theme within a protocol."""
    name: str = Field(alias="Name")
    purpose: str = Field(alias="Purpose of This Theme")
    why_matters: str = Field(alias="Why This Matters")
    outcomes: ThemeOutcomes = Field(alias="Outcomes")
    guiding_questions: List[str] = Field(alias="Guiding Questions")

    class Config:
        populate_by_name = True


class OverallOutcomes(BaseModel):
    """Overall outcomes for the protocol."""
    poor: str = Field(alias="Poor")
    expected: str = Field(alias="Expected")
    excellent: str = Field(alias="Excellent")
    transcendent: str = Field(alias="Transcendent")

    class Config:
        populate_by_name = True


class ProtocolMetadata(BaseModel):
    """Metadata for a protocol."""
    complexity: Optional[int] = Field(None, alias="Complexity")
    readiness_stage: Optional[str] = Field(None, alias="Readiness Stage")
    modes: List[str] = Field(default_factory=list, alias="Modes")
    estimated_time: Optional[str] = Field(None, alias="Estimated Time")
    tone_markers: List[str] = Field(default_factory=list, alias="Tone Markers")
    primary_scenarios: List[str] = Field(default_factory=list, alias="Primary Scenarios")
    related_protocols: List[str] = Field(default_factory=list, alias="Related Protocols")
    tags: List[str] = Field(default_factory=list, alias="Tags")
    algorithm: Optional[Dict[str, Any]] = Field(None, alias="Algorithm")
    stones: List[str] = Field(default_factory=list, alias="Stones")
    fields: List[str] = Field(default_factory=list, alias="Fields")
    bridges: List[str] = Field(default_factory=list, alias="Bridges")

    class Config:
        populate_by_name = True


class Protocol(BaseModel):
    """Complete Lichen Protocol structure."""
    title: str = Field(alias="Title")
    short_title: str = Field(alias="Short Title")
    overall_purpose: str = Field(alias="Overall Purpose")
    why_matters: str = Field(alias="Why This Matters")
    when_to_use: str = Field(alias="When To Use This Protocol")
    overall_outcomes: OverallOutcomes = Field(alias="Overall Outcomes")
    themes: List[Theme] = Field(alias="Themes")
    completion_prompts: List[str] = Field(alias="Completion Prompts")
    version: Optional[str] = Field(None, alias="Version")
    created_at: Optional[str] = Field(None, alias="Created At")
    protocol_id: Optional[str] = Field(None, alias="Protocol ID")
    category: Optional[str] = Field(None, alias="Category")
    metadata: Optional[ProtocolMetadata] = Field(None, alias="Metadata")

    class Config:
        populate_by_name = True


class ChunkMetadata(BaseModel):
    """Metadata for a chunk."""
    chunk_id: str
    protocol_id: str
    title: str
    section_name: str
    section_idx: int
    chunk_idx: int
    n_tokens: int
    source_path: str
    stones: List[str] = Field(default_factory=list)
    created_at: str
    hash: str
    profile: Optional[str] = None
    fusion_info: Optional[Dict[str, Any]] = None


class Chunk(BaseModel):
    """A chunk of text with metadata."""
    text: str
    metadata: ChunkMetadata


class SearchResult(BaseModel):
    """A search result with score and metadata."""
    score: float
    text_preview: str
    metadata: ChunkMetadata


class ProcessingResult(BaseModel):
    """Result of processing a protocol file."""
    file_path: str
    protocol_id: str
    valid: bool
    error_message: Optional[str] = None
    chunks_created: int = 0
    chunks_file: Optional[str] = None
