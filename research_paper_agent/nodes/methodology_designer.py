"""Methodology Designer — Node 11."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_strong
from research_paper_agent.schemas.design import Methodology
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.design_prompts import METHODOLOGY_DESIGNER_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def methodology_designer_node(state: ResearchPaperState) -> dict:
    node = "methodology_designer"
    try:
        designer = llm_strong.with_structured_output(Methodology)
        result = designer.invoke([
            SystemMessage(content=METHODOLOGY_DESIGNER_SYSTEM),
            HumanMessage(content=(
                f"Selected hypothesis:\n{state.get('selected_hypothesis', {})}\n\n"
                f"Domain analysis:\n{state.get('domain_analysis', {})}\n\n"
                f"Paper type: {state.get('paper_type', 'technical')}"
            )),
        ])
        return {"methodology": result.model_dump(),
                "execution_log": [make_log_entry(node, "SUCCESS", f"steps={len(result.steps)}")]}
    except Exception as exc:
        return {"methodology": {"approach": "To be determined", "steps": [], "assumptions": [],
                "limitations": [], "innovation_points": [], "required_data": [], "evaluation_strategy": ""},
                "errors": [make_error_entry(node, exc, fallback_used="empty_methodology")],
                "execution_log": [make_log_entry(node, "DEGRADED", str(exc))]}
