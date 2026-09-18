"""Citation Manager — Node 19."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_fast
from research_paper_agent.schemas.drafting import CitationPlan
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.drafting_prompts import CITATION_MANAGER_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def citation_manager_node(state: ResearchPaperState) -> dict:
    node = "citation_manager"
    merged = state.get("merged_paper_tex", "")
    if not merged:
        return {"bib_entries": [], "references_bib": "", "citation_report": None,
                "execution_log": [make_log_entry(node, "SKIP", "no merged paper")]}
    try:
        manager = llm_fast.with_structured_output(CitationPlan)
        plan = manager.invoke([
            SystemMessage(content=CITATION_MANAGER_SYSTEM),
            HumanMessage(content=(
                f"Paper body (LaTeX):\n{merged[:8000]}\n\n"
                f"Validated sources:\n{state.get('validated_sources', [])[:15]}\n\n"
                f"Evidence chunks:\n{state.get('evidence_chunks', [])[:15]}\n\n"
                f"Bibliography strategy: {state.get('paper_outline', {}).get('bibliography_strategy', 'ieee')}"
            )),
        ])
        # Build .bib file content
        from research_paper_agent.schemas.drafting import BibEntry
        bib_entries = [e.model_dump() for e in plan.bib_entries]
        bib_content = "\n\n".join(BibEntry(**e).to_bibtex() for e in bib_entries)
        # Validation
        import re
        cited_keys = set(re.findall(r"\\cite\{([^}]+)\}", plan.tex_with_citations))
        bib_keys = {e["key"] for e in bib_entries}
        orphans = list(cited_keys - bib_keys)
        report = {"total_citations": len(cited_keys), "unique_sources": len(bib_keys),
                  "orphan_citations": orphans, "missing_bib_entries": orphans,
                  "duplicate_keys": [], "is_valid": len(orphans) == 0}

        return {"merged_paper_tex": plan.tex_with_citations or merged,
                "bib_entries": bib_entries, "references_bib": bib_content,
                "citation_report": report,
                "execution_log": [make_log_entry(node, "SUCCESS",
                                  f"citations={len(cited_keys)} bib_entries={len(bib_entries)}")]}
    except Exception as exc:
        return {"bib_entries": [], "references_bib": "", "citation_report": None,
                "errors": [make_error_entry(node, exc, fallback_used="no_citations")],
                "execution_log": [make_log_entry(node, "DEGRADED", str(exc))]}
