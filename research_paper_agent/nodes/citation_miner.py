"""Citation Miner — Node 4."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_fast
from research_paper_agent.schemas.research import CitationNetwork
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.research_prompts import CITATION_MINER_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def citation_miner_node(state: ResearchPaperState) -> dict:
    node = "citation_miner"
    sources = state.get("validated_sources", [])
    if not sources:
        return {"citation_graph": [], "execution_log": [make_log_entry(node, "SKIP", "no sources")]}
    try:
        miner = llm_fast.with_structured_output(CitationNetwork)
        network = miner.invoke([
            SystemMessage(content=CITATION_MINER_SYSTEM),
            HumanMessage(content=f"Validated sources:\n{sources[:20]}"),
        ])
        edges = [e.model_dump() for e in network.edges]
        return {"citation_graph": edges, "execution_log": [make_log_entry(node, "SUCCESS", f"edges={len(edges)}")]}
    except Exception as exc:
        return {"citation_graph": [], "errors": [make_error_entry(node, exc, fallback_used="empty_graph")],
                "execution_log": [make_log_entry(node, "DEGRADED", str(exc))]}
