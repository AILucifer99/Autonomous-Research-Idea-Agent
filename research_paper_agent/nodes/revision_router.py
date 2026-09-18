"""Revision Router — selects failing sections and fans out to section_writer."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_fast
from research_paper_agent.schemas.review import RevisionDirective
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.errors import make_error_entry, make_log_entry

def revision_router_node(state: ResearchPaperState) -> dict:
    node = "revision_router"
    rev = state.get("revision_count", 0)
    try:
        router = llm_fast.with_structured_output(RevisionDirective)
        directive = router.invoke([
            SystemMessage(content="You are a revision coordinator. Based on review feedback and quality scores, "
                         "identify which sections need revision and provide specific instructions."),
            HumanMessage(content=(
                f"Review feedback:\n{state.get('review_feedback', [])}\n\n"
                f"Quality scores:\n{state.get('quality_scores', {})}\n\n"
                f"Paper outline sections:\n{[s.get('id') for s in state.get('paper_outline', {}).get('sections', [])]}"
            )),
        ])
        return {
            "revision_directive": directive.model_dump(),
            "revision_count": rev + 1,
            "sections_to_revise": directive.sections_to_revise,
            "execution_log": [make_log_entry(node, "SUCCESS",
                              f"sections_to_revise={directive.sections_to_revise}")],
        }
    except Exception as exc:
        # Fallback: revise all sections
        all_ids = [s["id"] for s in state.get("paper_outline", {}).get("sections", [])]
        return {
            "revision_directive": {"sections_to_revise": all_ids, "revision_notes": {}, "priority_issues": []},
            "revision_count": rev + 1,
            "sections_to_revise": all_ids,
            "errors": [make_error_entry(node, exc, fallback_used="revise_all")],
            "execution_log": [make_log_entry(node, "DEGRADED", str(exc))],
        }
