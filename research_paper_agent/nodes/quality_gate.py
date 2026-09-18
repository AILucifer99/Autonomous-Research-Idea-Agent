"""Quality Gate — routing node. Follows existing route_next() pattern."""
from __future__ import annotations
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.config import QUALITY_GATE_THRESHOLD, MAX_REVISION_ITERATIONS
from research_paper_agent.errors import make_log_entry

def quality_gate_node(state: ResearchPaperState) -> dict:
    """Pure routing node — checks quality scores and decides next step."""
    node = "quality_gate"
    scores = state.get("quality_scores") or {}
    overall = scores.get("overall", 0)
    rev = state.get("revision_count", 0)
    passes = overall >= QUALITY_GATE_THRESHOLD or rev >= MAX_REVISION_ITERATIONS
    return {
        "execution_log": [make_log_entry(node, "PASS" if passes else "REVISE",
                          f"overall={overall} revision={rev}/{MAX_REVISION_ITERATIONS}")],
    }
