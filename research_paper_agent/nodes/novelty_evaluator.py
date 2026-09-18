"""Novelty Evaluator — Node 10. Conditional routing: loop or proceed."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_strong
from research_paper_agent.schemas.innovation import NoveltyAssessment
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.innovation_prompts import NOVELTY_EVALUATOR_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def novelty_evaluator_node(state: ResearchPaperState) -> dict:
    node = "novelty_evaluator"
    iteration = state.get("novelty_iteration", 0)
    try:
        evaluator = llm_strong.with_structured_output(NoveltyAssessment)
        result = evaluator.invoke([
            SystemMessage(content=NOVELTY_EVALUATOR_SYSTEM),
            HumanMessage(content=(
                f"Selected hypothesis:\n{state.get('selected_hypothesis', {})}\n\n"
                f"Evidence chunks:\n{state.get('evidence_chunks', [])[:15]}\n\n"
                f"Knowledge graph:\n{state.get('knowledge_graph', {})}"
            )),
        ])
        return {"novelty_score": result.novelty_score, "novelty_assessment": result.model_dump(),
                "novelty_iteration": iteration + 1,
                "execution_log": [make_log_entry(node, "SUCCESS", f"score={result.novelty_score}")]}
    except Exception as exc:
        return {"novelty_score": 6.0, "novelty_assessment": None, "novelty_iteration": iteration + 1,
                "errors": [make_error_entry(node, exc, fallback_used="default_score")],
                "execution_log": [make_log_entry(node, "DEGRADED", str(exc))]}
