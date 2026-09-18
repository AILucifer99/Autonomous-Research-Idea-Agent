"""Gap Analyzer — Node 8. Conditional routing: loop back or proceed."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_strong
from research_paper_agent.schemas.knowledge import GapAnalysis
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.knowledge_prompts import GAP_ANALYZER_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def gap_analyzer_node(state: ResearchPaperState) -> dict:
    node = "gap_analyzer"
    try:
        analyzer = llm_strong.with_structured_output(GapAnalysis)
        result = analyzer.invoke([
            SystemMessage(content=GAP_ANALYZER_SYSTEM),
            HumanMessage(content=(
                f"Domain analysis:\n{state.get('domain_analysis', {})}\n\n"
                f"Knowledge graph:\n{state.get('knowledge_graph', {})}\n\n"
                f"Evidence chunks:\n{state.get('evidence_chunks', [])[:15]}\n\n"
                f"Research iteration: {state.get('research_iteration', 0)}"
            )),
        ])
        gaps = [g.model_dump() for g in result.gaps]
        return {"research_gaps": gaps, "gap_severity": result.overall_severity,
                "execution_log": [make_log_entry(node, "SUCCESS",
                                  f"gaps={len(gaps)} severity={result.overall_severity}")]}
    except Exception as exc:
        return {"research_gaps": [], "gap_severity": "minor",
                "errors": [make_error_entry(node, exc, fallback_used="no_gaps")],
                "execution_log": [make_log_entry(node, "DEGRADED", str(exc))]}
