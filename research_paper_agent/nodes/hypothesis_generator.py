"""Hypothesis Generator — Node 9."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_strong
from research_paper_agent.schemas.innovation import HypothesisSet
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.innovation_prompts import HYPOTHESIS_GENERATOR_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def hypothesis_generator_node(state: ResearchPaperState) -> dict:
    node = "hypothesis_generator"
    try:
        generator = llm_strong.with_structured_output(HypothesisSet)
        result = generator.invoke([
            SystemMessage(content=HYPOTHESIS_GENERATOR_SYSTEM),
            HumanMessage(content=(
                f"Research gaps:\n{state.get('research_gaps', [])}\n\n"
                f"Domain analysis:\n{state.get('domain_analysis', {})}\n\n"
                f"Knowledge graph:\n{state.get('knowledge_graph', {})}\n\n"
                f"Topic: {state['topic']}"
            )),
        ])
        hypotheses = [h.model_dump() for h in result.hypotheses]
        selected = hypotheses[result.selected_index] if hypotheses else None
        return {"hypotheses": hypotheses, "selected_hypothesis": selected,
                "execution_log": [make_log_entry(node, "SUCCESS", f"hypotheses={len(hypotheses)}")]}
    except Exception as exc:
        fallback = {"id": 1, "statement": f"Novel approach to {state['topic']}",
                    "rationale": "Based on identified gaps", "testability_score": 5.0,
                    "novelty_indicators": [], "assumptions": [], "related_gap_ids": [], "category": "empirical"}
        return {"hypotheses": [fallback], "selected_hypothesis": fallback,
                "errors": [make_error_entry(node, exc, fallback_used="generic_hypothesis")],
                "execution_log": [make_log_entry(node, "DEGRADED", str(exc))]}
