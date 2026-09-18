"""Outline Generator — Node 16. Follows existing orchestrator_node pattern."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_fast
from research_paper_agent.schemas.drafting import PaperOutline
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.drafting_prompts import OUTLINE_GENERATOR_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def outline_generator_node(state: ResearchPaperState) -> dict:
    node = "outline_generator"
    try:
        planner = llm_fast.with_structured_output(PaperOutline)
        outline = planner.invoke([
            SystemMessage(content=OUTLINE_GENERATOR_SYSTEM),
            HumanMessage(content=(
                f"Research plan:\n{state.get('research_plan', {})}\n\n"
                f"Selected hypothesis:\n{state.get('selected_hypothesis', {})}\n\n"
                f"Methodology:\n{state.get('methodology', {})}\n\n"
                f"Math artifacts count: {len(state.get('math_artifacts', []))}\n"
                f"Experiment design:\n{state.get('experiment_design', {})}\n\n"
                f"Figure specs count: {len(state.get('figure_specs', []))}\n"
                f"Evidence chunks count: {len(state.get('evidence_chunks', []))}\n"
                f"Target venue: {state.get('target_venue', 'arxiv')}\n"
                f"Paper type: {state.get('paper_type', 'technical')}\n"
                f"Master Orchestrator Strategy: {state.get('orchestrator_strategy', {})}"
            )),
        ])
        return {"paper_outline": outline.model_dump(),
                "execution_log": [make_log_entry(node, "SUCCESS", f"sections={len(outline.sections)}")]}
    except Exception as exc:
        # Minimal fallback outline
        from research_paper_agent.config import DEFAULT_SECTIONS
        fallback_sections = [
            {"id": i, "title": s, "section_type": s.lower().replace(" ", "_"),
             "goal": f"Cover {s}", "key_points": ["Point 1", "Point 2", "Point 3"],
             "target_words": 500, "assigned_evidence_ids": [], "assigned_math_ids": [],
             "assigned_figure_ids": [], "requires_citations": True,
             "requires_methodology": False, "requires_math": False}
            for i, s in enumerate(DEFAULT_SECTIONS)
        ]
        return {"paper_outline": {"paper_title": state["topic"], "abstract_plan": "",
                "sections": fallback_sections, "bibliography_strategy": "ieee"},
                "errors": [make_error_entry(node, exc, fallback_used="default_outline")],
                "execution_log": [make_log_entry(node, "DEGRADED", str(exc))]}
