"""Domain Expert — Node 7. Uses strong model for deep reasoning."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_strong
from research_paper_agent.schemas.knowledge import DomainAnalysis
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.knowledge_prompts import DOMAIN_EXPERT_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def domain_expert_node(state: ResearchPaperState) -> dict:
    node = "domain_expert"
    try:
        expert = llm_strong.with_structured_output(DomainAnalysis)
        analysis = expert.invoke([
            SystemMessage(content=DOMAIN_EXPERT_SYSTEM),
            HumanMessage(content=(
                f"Research topic: {state['topic']}\n"
                f"Knowledge graph:\n{state.get('knowledge_graph', {})}\n\n"
                f"Evidence chunks:\n{state.get('evidence_chunks', [])[:20]}\n\n"
                f"Research plan:\n{state.get('research_plan', {})}"
            )),
        ])
        return {"domain_analysis": analysis.model_dump(),
                "execution_log": [make_log_entry(node, "SUCCESS", f"trends={len(analysis.key_trends)}")]}
    except Exception as exc:
        return {"domain_analysis": {"field_summary": f"Analysis of {state['topic']}", "key_trends": [],
                "contradictions": [], "limitations_in_literature": [], "opportunities": [], "maturity_level": "growing"},
                "errors": [make_error_entry(node, exc, fallback_used="basic_analysis")],
                "execution_log": [make_log_entry(node, "DEGRADED", str(exc))]}
