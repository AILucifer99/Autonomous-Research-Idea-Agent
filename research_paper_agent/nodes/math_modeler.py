"""Mathematical Modeler — Node 12. Uses strong model for math reasoning."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_strong
from research_paper_agent.schemas.design import MathModelingResult
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.design_prompts import MATH_MODELER_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def math_modeler_node(state: ResearchPaperState) -> dict:
    node = "math_modeler"
    try:
        modeler = llm_strong.with_structured_output(MathModelingResult)
        result = modeler.invoke([
            SystemMessage(content=MATH_MODELER_SYSTEM),
            HumanMessage(content=(
                f"Methodology:\n{state.get('methodology', {})}\n\n"
                f"Selected hypothesis:\n{state.get('selected_hypothesis', {})}\n\n"
                f"Paper type: {state.get('paper_type', 'technical')}"
            )),
        ])
        artifacts = [a.model_dump() for a in result.artifacts]
        return {"math_artifacts": artifacts,
                "execution_log": [make_log_entry(node, "SUCCESS", f"artifacts={len(artifacts)}")]}
    except Exception as exc:
        return {"math_artifacts": [],
                "errors": [make_error_entry(node, exc, fallback_used="no_math")],
                "execution_log": [make_log_entry(node, "DEGRADED", str(exc))]}
