"""
Research Planner Agent — Node 1.

Follows the existing orchestrator_node pattern (bwa_backend.py L263-287):
    llm.with_structured_output(Schema).invoke([SystemMessage, HumanMessage])
"""

from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from research_paper_agent.llm import llm_fast
from research_paper_agent.schemas.research import ResearchPlan
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.research_prompts import RESEARCH_PLANNER_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry, NonRetryableError
from research_paper_agent.config import MAX_RESEARCH_ITERATIONS


def research_planner_node(state: ResearchPaperState) -> dict:
    """Analyse topic and produce a research plan with search queries."""
    node = "research_planner"
    iteration = state.get("research_iteration", 0)

    # Guard: do not exceed max iterations
    if iteration >= MAX_RESEARCH_ITERATIONS:
        return {
            "execution_log": [make_log_entry(node, "SKIP", f"max iterations ({MAX_RESEARCH_ITERATIONS}) reached")],
        }

    try:
        # Build context including any gap-analysis feedback
        gap_context = ""
        if state.get("research_gaps"):
            gap_context = f"\n\nPrevious gap analysis found gaps. Supplementary queries needed:\n{state['research_gaps']}"

        orchestrator_context = ""
        if state.get("orchestrator_strategy"):
            strat = state["orchestrator_strategy"]
            orchestrator_context = (
                f"\n\nMaster Orchestrator Strategy:\n"
                f"- Guidance: {strat.get('strategic_guidance')}\n"
                f"- Focus Areas: {strat.get('core_focus_areas')}\n"
            )

        planner = llm_fast.with_structured_output(ResearchPlan)
        plan = planner.invoke([
            SystemMessage(content=RESEARCH_PLANNER_SYSTEM),
            HumanMessage(content=(
                f"Topic: {state['topic']}\n"
                f"Paper type: {state.get('paper_type', 'technical')}\n"
                f"Target venue: {state.get('target_venue', 'arxiv')}\n"
                f"User preferences: {state.get('user_preferences', {})}\n"
                f"Iteration: {iteration + 1}/{MAX_RESEARCH_ITERATIONS}\n"
                f"As-of date: {state.get('as_of', '')}\n"
                f"{orchestrator_context}"
                f"{gap_context}"
            )),
        ])

        queries = [q.model_dump() for q in plan.queries]

        return {
            "research_plan": plan.model_dump(),
            "search_queries": queries,
            "research_iteration": iteration + 1,
            "execution_log": [make_log_entry(node, "SUCCESS", f"queries={len(queries)}")],
        }

    except Exception as exc:
        # Fallback: minimal plan with generic queries
        fallback_queries = [
            {"id": 1, "query_text": f"{state['topic']} survey", "source_type": "academic", "priority": "high"},
            {"id": 2, "query_text": f"{state['topic']} recent advances", "source_type": "academic", "priority": "high"},
            {"id": 3, "query_text": f"{state['topic']} methodology", "source_type": "technical", "priority": "medium"},
            {"id": 4, "query_text": f"{state['topic']} challenges limitations", "source_type": "academic", "priority": "medium"},
            {"id": 5, "query_text": f"{state['topic']} state of the art", "source_type": "academic", "priority": "medium"},
        ]
        return {
            "research_plan": {
                "title_working": state["topic"],
                "field": "Computer Science",
                "sub_field": "General",
                "research_question": f"What are the key challenges and opportunities in {state['topic']}?",
                "depth_level": "deep",
                "queries": fallback_queries,
                "expected_sections": [],
                "methodology_notes": "",
            },
            "search_queries": fallback_queries,
            "research_iteration": iteration + 1,
            "errors": [make_error_entry(node, exc, fallback_used="generic_queries")],
            "execution_log": [make_log_entry(node, "DEGRADED", str(exc))],
        }
