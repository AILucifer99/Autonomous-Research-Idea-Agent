"""
Research Paper Agent — Backend Service.

Provides programmatic execution and streaming wrappers around the compiled
LangGraph research paper workflow, matching the existing bwa_backend.py patterns.
"""

from __future__ import annotations

import io
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

from research_paper_agent.graph import research_paper_app
from research_paper_agent.schemas.state import ResearchPaperState


def safe_slug(text: str) -> str:
    """Sanitize title or topic into a directory/file-safe slug."""
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9 _-]+", "", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s[:60] or "paper"


def build_initial_state(
    topic: str,
    paper_type: str = "technical",
    target_venue: str = "arxiv",
    user_preferences: Optional[Dict[str, Any]] = None,
    compact_mode: bool = False,
    human_approved: bool = True,
) -> ResearchPaperState:
    """Build a clean initial state dictionary for pipeline execution."""
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = safe_slug(topic)
    out_dir = os.path.join("output", slug)

    return {
        "topic": topic,
        "paper_type": paper_type,
        "target_venue": target_venue,
        "user_preferences": user_preferences or {},
        "pre_flight_estimate": None,
        "human_approved": human_approved,
        "compact_mode": compact_mode,
        "orchestrator_strategy": None,
        "orchestrator_directives": [],
        "research_plan": None,
        "search_queries": [],
        "raw_literature": [],
        "validated_sources": [],
        "rejected_sources": [],
        "citation_graph": [],
        "evidence_chunks": [],
        "knowledge_graph": {},
        "domain_analysis": None,
        "research_gaps": [],
        "gap_severity": "none",
        "research_iteration": 0,
        "hypotheses": [],
        "selected_hypothesis": None,
        "novelty_score": 0.0,
        "novelty_assessment": None,
        "novelty_iteration": 0,
        "methodology": None,
        "math_artifacts": [],
        "experiment_design": None,
        "analysis_results": None,
        "figure_specs": [],
        "paper_outline": None,
        "drafted_sections": [],
        "merged_paper_tex": "",
        "bib_entries": [],
        "references_bib": "",
        "citation_report": None,
        "generated_figures": [],
        "review_feedback": [],
        "quality_scores": None,
        "revision_count": 0,
        "revision_directive": None,
        "sections_to_revise": [],
        "latex_document": "",
        "latex_valid": False,
        "latex_errors": [],
        "final_tex": "",
        "final_bib": "",
        "final_pdf_path": "",
        "final_markdown": "",
        "final_markdown_path": "",
        "output_dir": out_dir,
        "traceability_report": "",
        "cost_summary": None,
        "llm_call_metrics": [],
        "errors": [],
        "execution_log": [],
        "as_of": as_of,
    }


def run_pipeline(
    topic: str,
    paper_type: str = "technical",
    target_venue: str = "arxiv",
    user_preferences: Optional[Dict[str, Any]] = None,
    compact_mode: bool = False,
    human_approved: bool = True,
) -> Dict[str, Any]:
    """Execute the entire multi-agent pipeline synchronously and return final state with cost tracking."""
    from research_paper_agent.cost_tracker import CostTrackerSession

    init_state = build_initial_state(
        topic=topic,
        paper_type=paper_type,
        target_venue=target_venue,
        user_preferences=user_preferences,
        compact_mode=compact_mode,
        human_approved=human_approved,
    )

    with CostTrackerSession() as tracker:
        final_state = research_paper_app.invoke(init_state)
        summary = tracker.get_summary()
        metrics = tracker.get_metrics()
        final_state["cost_summary"] = summary
        final_state["llm_call_metrics"] = metrics

        out_dir = final_state.get("output_dir")
        if out_dir:
            try:
                tracker.export_json(os.path.join(out_dir, "cost_summary.json"))
            except Exception:
                pass

        return final_state


def stream_pipeline(
    topic: str,
    paper_type: str = "technical",
    target_venue: str = "arxiv",
    user_preferences: Optional[Dict[str, Any]] = None,
    compact_mode: bool = False,
    human_approved: bool = True,
) -> Iterator[Tuple[str, Any]]:
    """
    Stream execution of the research paper agent pipeline.

    Yields:
      ("updates", {node_name: partial_state})
      or ("final", complete_state)
    """
    from research_paper_agent.cost_tracker import CostTrackerSession

    init_state = build_initial_state(
        topic=topic,
        paper_type=paper_type,
        target_venue=target_venue,
        user_preferences=user_preferences,
        compact_mode=compact_mode,
        human_approved=human_approved,
    )

    with CostTrackerSession() as tracker:
        accumulated_state: Dict[str, Any] = dict(init_state)
        list_reducers = {
            "raw_literature",
            "drafted_sections",
            "review_feedback",
            "errors",
            "execution_log",
            "llm_call_metrics",
        }

        try:
            for chunk in research_paper_app.stream(init_state, stream_mode="updates"):
                yield ("updates", chunk)
                if isinstance(chunk, dict):
                    for node_name, node_update in chunk.items():
                        if isinstance(node_update, dict):
                            for k, v in node_update.items():
                                if k in list_reducers and isinstance(v, list):
                                    accumulated_state[k] = list(accumulated_state.get(k, [])) + v
                                else:
                                    accumulated_state[k] = v

            # Final pass: attach cost summary and yield complete state without re-running graph
            summary = tracker.get_summary()
            metrics = tracker.get_metrics()
            accumulated_state["cost_summary"] = summary
            accumulated_state["llm_call_metrics"] = metrics

            out_dir = accumulated_state.get("output_dir")
            if out_dir:
                try:
                    tracker.export_json(os.path.join(out_dir, "cost_summary.json"))
                except Exception:
                    pass

            yield ("final", accumulated_state)
            return

        except Exception as exc:
            logger_err = f"Streaming updates encountered error: {exc}"
            accumulated_state.setdefault("errors", []).append({"node": "stream_pipeline", "error": str(exc)})

        # Fallback to single invoke if streaming completely failed
        final_state = research_paper_app.invoke(init_state)
        summary = tracker.get_summary()
        metrics = tracker.get_metrics()
        final_state["cost_summary"] = summary
        final_state["llm_call_metrics"] = metrics
        yield ("final", final_state)


def bundle_paper_zip(output_dir: str) -> Optional[bytes]:
    """Package the generated paper directory (.tex, .bib, .pdf, figures, report) into a ZIP."""
    p = Path(output_dir)
    if not p.exists() or not p.is_dir():
        return None

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for file_path in p.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(p)
                z.write(file_path, arcname=str(arcname))
    return buf.getvalue()


__all__ = [
    "research_paper_app",
    "safe_slug",
    "build_initial_state",
    "run_pipeline",
    "stream_pipeline",
    "bundle_paper_zip",
]
