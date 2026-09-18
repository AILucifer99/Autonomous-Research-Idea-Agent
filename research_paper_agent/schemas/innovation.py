"""
Innovation schemas: hypotheses, novelty evaluation.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

__all__ = [
    "Hypothesis",
    "HypothesisSet",
    "NoveltyAssessment",
]


class Hypothesis(BaseModel):
    id: int
    statement: str
    rationale: str
    testability_score: float = Field(ge=0.0, le=10.0, default=5.0)
    novelty_indicators: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    related_gap_ids: List[int] = Field(default_factory=list)
    category: Literal["theoretical", "empirical", "methodological", "applied"] = "empirical"


class HypothesisSet(BaseModel):
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    selected_index: int = Field(0, description="Index of the recommended hypothesis")


class NoveltyAssessment(BaseModel):
    novelty_score: float = Field(ge=0.0, le=10.0, default=5.0)
    existing_similar_works: List[str] = Field(default_factory=list)
    differentiation_points: List[str] = Field(default_factory=list)
    potential_contributions: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recommendation: Literal["accept", "revise", "reject"] = "accept"
