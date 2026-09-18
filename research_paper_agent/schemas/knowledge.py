"""
Knowledge synthesis schemas: knowledge graph, domain analysis, gaps.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

__all__ = [
    "KnowledgeNode",
    "KnowledgeEdge",
    "KnowledgeCluster",
    "KnowledgeGraph",
    "DomainAnalysis",
    "ResearchGap",
    "GapAnalysis",
]


class KnowledgeNode(BaseModel):
    id: int
    label: str
    node_type: Literal["concept", "method", "dataset", "metric", "tool", "theory", "finding"] = "concept"
    description: str = ""
    source_ids: List[int] = Field(default_factory=list)


class KnowledgeEdge(BaseModel):
    source_id: int
    target_id: int
    relationship: Literal["related_to", "extends", "contradicts", "uses", "evaluates", "produces", "part_of"] = "related_to"
    weight: float = Field(ge=0.0, le=1.0, default=0.5)


class KnowledgeCluster(BaseModel):
    cluster_id: int
    label: str
    node_ids: List[int] = Field(default_factory=list)
    summary: str = ""


class KnowledgeGraph(BaseModel):
    nodes: List[KnowledgeNode] = Field(default_factory=list)
    edges: List[KnowledgeEdge] = Field(default_factory=list)
    clusters: List[KnowledgeCluster] = Field(default_factory=list)


class DomainAnalysis(BaseModel):
    field_summary: str
    key_trends: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    limitations_in_literature: List[str] = Field(default_factory=list)
    opportunities: List[str] = Field(default_factory=list)
    maturity_level: Literal["emerging", "growing", "mature", "declining"] = "growing"


class ResearchGap(BaseModel):
    id: int = 0
    description: str
    significance: Literal["critical", "major", "minor"] = "major"
    potential_approach: str = ""
    related_evidence_ids: List[int] = Field(default_factory=list)


class GapAnalysis(BaseModel):
    gaps: List[ResearchGap] = Field(default_factory=list)
    overall_severity: Literal["critical", "moderate", "minor", "none"] = "moderate"
    supplementary_queries: List[str] = Field(default_factory=list)
