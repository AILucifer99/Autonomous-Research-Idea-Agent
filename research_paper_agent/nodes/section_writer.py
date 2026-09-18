"""
Section Writer Worker — Node 17 (parallel, receives Send() payload).
Follows existing worker_node(payload: dict) -> dict pattern.
"""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import extract_text_content, llm_fast
from research_paper_agent.prompts.drafting_prompts import SECTION_WRITER_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def section_writer_node(payload: dict) -> dict:
    """Draft one section of the paper in LaTeX."""
    node = "section_writer"
    section = payload.get("section_task", {})
    section_id = section.get("id", 0)
    section_title = section.get("title", f"Section {section_id}")
    outline = payload.get("paper_outline", {})

    try:
        evidence_text = "\n".join(f"- [{e.get('source_title', '')}] {e.get('key_finding', '')}"
                                for e in payload.get("evidence_chunks", [])[:5])
        math_text = "\n".join(f"- {m.get('name', '')}: ${m.get('latex', '')}$"
                              for m in payload.get("math_artifacts", [])[:3])
        key_points_text = "\n- ".join(section.get("key_points", []))

        # Include revision notes if revising
        revision_context = ""
        if payload.get("revision_notes"):
            revision_context = f"\n\nRevision notes for this section:\n{payload['revision_notes']}"

        raw_response = llm_fast.invoke([
            SystemMessage(content=SECTION_WRITER_SYSTEM),
            HumanMessage(content=(
                f"Paper title: {payload.get('paper_outline', {}).get('paper_title', '')}\n"
                f"Target venue: {payload.get('target_venue', 'arxiv')}\n\n"
                f"Section: {section_title}\n"
                f"Section type: {section.get('section_type', '')}\n"
                f"Goal: {section.get('goal', '')}\n"
                f"Target words: {section.get('target_words', 500)}\n"
                f"Requires citations: {section.get('requires_citations', True)}\n"
                f"Requires math: {section.get('requires_math', False)}\n\n"
                f"Key points:\n- {key_points_text}\n\n"
                f"Available evidence:\n{evidence_text}\n\n"
                f"Math artifacts:\n{math_text}\n"
                f"{revision_context}"
            )),
        ])
        content = extract_text_content(raw_response.content)

        return {
            "drafted_sections": [(section_id, content)],
            "execution_log": [make_log_entry(node, "SUCCESS",
                              f"section={section_id} title={section_title}")],
        }

    except Exception as exc:
        placeholder = f"\\section{{{section_title}}}\n% [SECTION PENDING — writer failed: {exc}]\n"
        return {
            "drafted_sections": [(section_id, placeholder)],
            "errors": [make_error_entry(node, exc, fallback_used="placeholder_section")],
            "execution_log": [make_log_entry(node, "FAILED", f"section={section_id}: {exc}")],
        }
