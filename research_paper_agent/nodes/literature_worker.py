"""
Literature Discovery Worker — Node 2 (parallel, receives Send() payload).

Follows the existing worker_node pattern (bwa_backend.py L336-374):
    def worker_node(payload: dict) -> dict
"""

from __future__ import annotations

from research_paper_agent.tools import tavily_search
from research_paper_agent.errors import make_error_entry, make_log_entry
from research_paper_agent.config import MAX_RESULTS_PER_QUERY


def literature_worker_node(payload: dict) -> dict:
    """Execute a single search query and return normalised results."""
    node = "literature_worker"
    query_data = payload.get("query", {})
    query_text = query_data.get("query_text", "") if isinstance(query_data, dict) else str(query_data)
    query_id = query_data.get("id", 0) if isinstance(query_data, dict) else 0

    try:
        raw = tavily_search(query_text, max_results=MAX_RESULTS_PER_QUERY)

        # Normalise into LiteratureResult dicts
        results = []
        for i, r in enumerate(raw):
            results.append({
                "id": query_id * 100 + i,
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "authors": None,
                "year": (r.get("published_at") or "")[:4] or None,
                "abstract": None,
                "snippet": r.get("snippet", ""),
                "source_db": "tavily",
            })

        return {
            "raw_literature": results,
            "execution_log": [make_log_entry(node, "SUCCESS", f"query_id={query_id} results={len(results)}")],
        }

    except Exception as exc:
        return {
            "raw_literature": [],
            "errors": [make_error_entry(node, exc, fallback_used="empty_results")],
            "execution_log": [make_log_entry(node, "FAILED", f"query_id={query_id}: {exc}")],
        }
