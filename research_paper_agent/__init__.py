"""
Research Paper Agent — Multi-Agent Research Paper Generation System.

A production-grade LangGraph pipeline that transforms a research topic
into a publication-ready LaTeX manuscript using coordinated Gemini-powered agents.
"""

from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.graph import research_paper_app
from research_paper_agent.backend import (
    run_pipeline,
    stream_pipeline,
    build_initial_state,
    bundle_paper_zip,
    safe_slug,
)
from research_paper_agent.cost_tracker import (
    CostTracker,
    LLMCallMetric,
    CostTrackingCallbackHandler,
    CostTrackerSession,
    get_current_tracker,
)

__version__ = "1.0.0"

__all__ = [
    "ResearchPaperState",
    "research_paper_app",
    "run_pipeline",
    "stream_pipeline",
    "build_initial_state",
    "bundle_paper_zip",
    "safe_slug",
    "CostTracker",
    "LLMCallMetric",
    "CostTrackingCallbackHandler",
    "CostTrackerSession",
    "get_current_tracker",
]
