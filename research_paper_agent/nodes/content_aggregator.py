"""Content Aggregator — Node 18. Follows existing merge_content pattern."""
from __future__ import annotations
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.errors import make_log_entry

def content_aggregator_node(state: ResearchPaperState) -> dict:
    """Merge drafted sections in order. Same pattern as merge_content (bwa_backend.py L380-387)."""
    node = "content_aggregator"
    outline = state.get("paper_outline")
    sections = state.get("drafted_sections", [])

    if not outline:
        return {"merged_paper_tex": "", "execution_log": [make_log_entry(node, "SKIP", "no outline")]}

    # Map latest section content by section_id (so revisions replace earlier drafts)
    latest_sections: dict[int, str] = {}
    for sid, tex in sections:
        latest_sections[sid] = tex

    expected_ids = {s["id"] for s in outline.get("sections", [])}
    present_ids = set(latest_sections.keys())
    missing = expected_ids - present_ids

    ordered = []
    for s in outline.get("sections", []):
        sid = s["id"]
        if sid in latest_sections:
            ordered.append(latest_sections[sid])
        else:
            title = s.get("title", f"Section {sid}")
            ordered.append(f"\\section{{{title}}}\n% [SECTION PENDING — not received from writer]\n")

    body = "\n\n".join(ordered).strip()
    title = outline.get("paper_title", "Research Paper")
    merged = f"% Title: {title}\n% Auto-generated LaTeX body\n\n{body}\n"

    return {
        "merged_paper_tex": merged,
        "execution_log": [make_log_entry(node, "SUCCESS",
                          f"sections={len(latest_sections)} missing={len(missing)}")],
    }
