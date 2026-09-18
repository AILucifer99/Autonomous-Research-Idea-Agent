"""
Source Validator — Node 3.
Follows the existing research_node deduplication pattern (bwa_backend.py L229-233).
"""

from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from research_paper_agent.llm import llm_fast
from research_paper_agent.schemas.research import ValidationBatch
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.research_prompts import SOURCE_VALIDATOR_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry


def source_validator_node(state: ResearchPaperState) -> dict:
    """Validate and deduplicate raw literature sources."""
    node = "source_validator"
    raw = state.get("raw_literature", [])

    if not raw:
        return {
            "validated_sources": [],
            "rejected_sources": [],
            "execution_log": [make_log_entry(node, "SKIP", "no raw literature to validate")],
        }

    # Deduplicate by URL first (existing pattern)
    dedup: dict = {}
    for item in raw:
        url = item.get("url", "")
        if url and url not in dedup:
            dedup[url] = item
    unique_sources = list(dedup.values())

    try:
        validator = llm_fast.with_structured_output(ValidationBatch)
        batch = validator.invoke([
            SystemMessage(content=SOURCE_VALIDATOR_SYSTEM),
            HumanMessage(content=(
                f"Research topic: {state['topic']}\n"
                f"Research plan: {state.get('research_plan', {})}\n\n"
                f"Sources to validate ({len(unique_sources)}):\n"
                f"{unique_sources[:30]}"
            )),
        ])

        validated = []
        rejected = []
        for vr in batch.results:
            # Find matching source
            matching = [s for s in unique_sources if s.get("url") == vr.source_url]
            source = matching[0] if matching else {"url": vr.source_url, "title": ""}
            entry = {
                "source": source,
                "credibility_score": vr.credibility_score,
                "relevance_score": vr.relevance_score,
                "is_valid": vr.is_valid,
                "rejection_reason": vr.rejection_reason,
            }
            if vr.is_valid:
                validated.append(entry)
            else:
                rejected.append(entry)

        return {
            "validated_sources": validated,
            "rejected_sources": rejected,
            "execution_log": [make_log_entry(node, "SUCCESS",
                              f"validated={len(validated)} rejected={len(rejected)}")],
        }

    except Exception as exc:
        # Fallback: pass all sources as unvalidated
        fallback = [{"source": s, "credibility_score": 5.0, "relevance_score": 5.0,
                      "is_valid": True, "rejection_reason": None} for s in unique_sources]
        return {
            "validated_sources": fallback,
            "rejected_sources": [],
            "errors": [make_error_entry(node, exc, fallback_used="all_sources_unvalidated")],
            "execution_log": [make_log_entry(node, "DEGRADED", str(exc))],
        }
