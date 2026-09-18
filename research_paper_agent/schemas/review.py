"""
Review-phase schemas: review feedback, quality scores, revision directives.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

__all__ = [
    "ReviewIssue",
    "ReviewFeedback",
    "QualityScores",
    "RevisionDirective",
]


class ReviewIssue(BaseModel):
    severity: Literal["critical", "major", "minor"] = "minor"
    section_id: Optional[int] = None
    description: str
    suggestion: str = ""


class ReviewFeedback(BaseModel):
    reviewer_type: Literal[
        "scientific", "factual", "consistency",
        "statistical", "reproducibility",
    ]
    score: float = Field(ge=0.0, le=10.0, default=5.0)
    issues: List[ReviewIssue] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    revision_instructions: str = ""


class QualityScores(BaseModel):
    technical_accuracy: float = Field(ge=0.0, le=10.0, default=5.0)
    novelty: float = Field(ge=0.0, le=10.0, default=5.0)
    methodology_quality: float = Field(ge=0.0, le=10.0, default=5.0)
    mathematical_rigor: float = Field(ge=0.0, le=10.0, default=5.0)
    citation_quality: float = Field(ge=0.0, le=10.0, default=5.0)
    coherence: float = Field(ge=0.0, le=10.0, default=5.0)
    reproducibility: float = Field(ge=0.0, le=10.0, default=5.0)
    publication_readiness: float = Field(ge=0.0, le=10.0, default=5.0)
    overall: float = Field(ge=0.0, le=10.0, default=5.0)
    passes_gate: bool = False
    summary: str = ""


class RevisionDirective(BaseModel):
    sections_to_revise: List[int] = Field(default_factory=list)
    revision_notes: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of section_id (str) → revision instructions",
    )
    priority_issues: List[str] = Field(default_factory=list)
