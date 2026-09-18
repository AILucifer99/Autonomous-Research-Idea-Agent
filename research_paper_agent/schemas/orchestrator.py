"""
Pydantic schemas for the Master Orchestrator, Orchestrator Guide, and Pre-Flight HITL authorization.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

__all__ = [
    "VenueProfile",
    "PreFlightEstimate",
    "OrchestratorDirective",
    "OrchestratorStrategy",
]


class VenueProfile(BaseModel):
    """Publication venue guidelines and rubric profile."""
    venue_key: str = Field(description="Normalized venue key e.g. ieee_conference, acm, nature, arxiv")
    display_name: str = Field(description="Human readable venue title")
    target_word_count: int = Field(default=6000, description="Recommended total manuscript word count")
    max_pages: Optional[int] = Field(default=None, description="Max page limit if applicable")
    recommended_sections: List[str] = Field(default_factory=list, description="Prescribed outline sections")
    tone: str = Field(default="formal, precise, academic", description="Stylistic register")
    math_depth: str = Field(default="rigorous", description="rigorous | applied | conceptual")
    citation_style: str = Field(default="numeric", description="IEEE numeric | ACM author-year | Nature superscripts")
    figure_count_target: int = Field(default=4, description="Target number of illustrative figures")
    key_rubrics: List[str] = Field(default_factory=list, description="Core criteria evaluated by peer reviewers")


class PreFlightEstimate(BaseModel):
    """Pre-flight resource, cost, and API call estimation for Human-in-the-Loop approval."""
    estimated_llm_calls: int = Field(description="Predicted LLM calls across all phases")
    estimated_search_queries: int = Field(description="Predicted web/Tavily search calls")
    estimated_image_calls: int = Field(description="Predicted Gemini image generation calls")
    estimated_total_tokens: int = Field(description="Predicted input + output tokens")
    estimated_cost_usd: float = Field(description="Estimated USD cost based on MODEL_PRICING")
    requires_human_confirmation: bool = Field(description="True if calls or cost exceed safe thresholds")
    reasons_for_confirmation: List[str] = Field(default_factory=list, description="Why HITL approval is triggered")
    compact_mode_available: bool = Field(default=True, description="Whether workflow can run in budget compact mode")
    estimated_duration_seconds: int = Field(default=90, description="Estimated total execution latency")


class OrchestratorDirective(BaseModel):
    """Actionable directive produced by the Master Orchestrator during quality meta-evaluation."""
    action: str = Field(description="proceed_to_publication | revise_sections | deep_research")
    target_sections: List[int] = Field(default_factory=list, description="Section indices to revise if applicable")
    instructions: str = Field(default="", description="Targeted guidance for the revision or synthesis nodes")
    composite_score: float = Field(default=0.0, description="Weighted composite score across reviewer feedback")
    component_scores: Dict[str, float] = Field(default_factory=dict, description="Normalized 0-10 sub-scores")
    venue_alignment_score: float = Field(default=0.0, description="Fit with venue conventions (0-10)")
    reasoning: str = Field(default="", description="Master Orchestrator's structured rationale")


class OrchestratorStrategy(BaseModel):
    """Initial overarching gameplan formulated by the Master Orchestrator."""
    venue_profile: VenueProfile = Field(description="Venue standards applied to this run")
    strategic_guidance: str = Field(description="High-level guidance injected into downstream agents")
    word_budget_allocation: Dict[str, int] = Field(default_factory=dict, description="Word targets per section")
    target_figure_count: int = Field(default=4, description="Prescribed number of visual artifacts")
    core_focus_areas: List[str] = Field(default_factory=list, description="Priority themes or angles")
    compact_mode: bool = Field(default=False, description="True if budget/speed compact mode is active")
