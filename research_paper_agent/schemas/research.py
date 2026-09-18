"""
Research-phase schemas: search queries, literature results, evidence.

Follows the existing EvidenceItem / EvidencePack pattern (bwa_backend.py L53-70).
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

__all__ = [
    "SearchQuery",
    "ResearchPlan",
    "LiteratureResult",
    "ValidatedSource",
    "CitationEdge",
    "CitationNetwork",
    "EvidenceChunk",
    "EvidenceExtractionResult",
    "ValidationResult",
    "ValidationBatch",
]


class SearchQuery(BaseModel):
    id: int
    query_text: str
    source_type: Literal["academic", "technical", "general"] = "academic"
    priority: Literal["high", "medium", "low"] = "medium"


class ResearchPlan(BaseModel):
    title_working: str
    field: str
    sub_field: str
    research_question: str
    depth_level: Literal["survey", "deep", "exploratory"] = "deep"
    queries: List[SearchQuery]
    expected_sections: List[str] = Field(default_factory=list)
    methodology_notes: str = ""


class LiteratureResult(BaseModel):
    id: int = 0
    title: str
    url: str
    authors: Optional[str] = None
    year: Optional[str] = None
    abstract: Optional[str] = None
    snippet: Optional[str] = None
    source_db: Optional[str] = None


class ValidatedSource(BaseModel):
    source: LiteratureResult
    credibility_score: float = Field(ge=0.0, le=10.0, default=5.0)
    relevance_score: float = Field(ge=0.0, le=10.0, default=5.0)
    is_valid: bool = True
    rejection_reason: Optional[str] = None


class ValidationResult(BaseModel):
    """LLM output for a single source validation."""
    source_url: str
    credibility_score: float = Field(ge=0.0, le=10.0)
    relevance_score: float = Field(ge=0.0, le=10.0)
    is_valid: bool = True
    rejection_reason: Optional[str] = None


class ValidationBatch(BaseModel):
    """LLM output for batch source validation."""
    results: List[ValidationResult] = Field(default_factory=list)


class CitationEdge(BaseModel):
    from_url: str
    to_url: str
    relationship: Literal["cites", "extends", "contradicts", "supports", "reviews"] = "cites"


class CitationNetwork(BaseModel):
    edges: List[CitationEdge] = Field(default_factory=list)


class EvidenceChunk(BaseModel):
    source_id: int = 0
    source_url: str = ""
    claim: str
    supporting_quote: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    evidence_type: Literal["finding", "method", "data", "theory", "definition"] = "finding"
    is_novel: bool = False


class EvidenceExtractionResult(BaseModel):
    evidence: List[EvidenceChunk] = Field(default_factory=list)
