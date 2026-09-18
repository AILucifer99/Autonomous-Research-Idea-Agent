"""Evidence Extractor — Node 5. Follows existing research_node LLM synthesis pattern."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_fast
from research_paper_agent.schemas.research import EvidenceExtractionResult
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.research_prompts import EVIDENCE_EXTRACTOR_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def evidence_extractor_node(state: ResearchPaperState) -> dict:
    node = "evidence_extractor"
    sources = state.get("validated_sources", [])
    if not sources:
        return {"evidence_chunks": [], "execution_log": [make_log_entry(node, "SKIP", "no sources")]}
    try:
        extractor = llm_fast.with_structured_output(EvidenceExtractionResult)
        result = extractor.invoke([
            SystemMessage(content=EVIDENCE_EXTRACTOR_SYSTEM),
            HumanMessage(content=(
                f"Research plan: {state.get('research_plan', {})}\n\n"
                f"Validated sources:\n{sources[:20]}"
            )),
        ])
        chunks = [c.model_dump() for c in result.evidence]
        return {"evidence_chunks": chunks, "execution_log": [make_log_entry(node, "SUCCESS", f"chunks={len(chunks)}")]}
    except Exception as exc:
        return {"evidence_chunks": [], "errors": [make_error_entry(node, exc, fallback_used="empty_evidence")],
                "execution_log": [make_log_entry(node, "DEGRADED", str(exc))]}
