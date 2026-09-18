"""Traceability Reporter — final node, generates provenance report."""
from __future__ import annotations
import os
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.errors import make_log_entry

def traceability_reporter_node(state: ResearchPaperState) -> dict:
    node = "traceability_reporter"
    output_dir = state.get("output_dir", "output/paper")

    from research_paper_agent.cost_tracker import get_current_tracker

    # Gather stats
    errors = state.get("errors", [])
    logs = state.get("execution_log", [])
    quality = state.get("quality_scores", {})
    feedback = state.get("review_feedback", [])
    sources = state.get("validated_sources", [])
    rev_count = state.get("revision_count", 0)

    # Cost summary
    cost_summary = state.get("cost_summary") or get_current_tracker().get_summary()

    report_lines = [
        "# Research Traceability Report",
        "",
        "## Execution Summary",
        f"- **Topic**: {state.get('topic', '')}",
        f"- **Paper Type**: {state.get('paper_type', '')}",
        f"- **Target Venue**: {state.get('target_venue', '')}",
        f"- **Total Nodes Executed**: {len(logs)}",
        f"- **Errors Encountered**: {len(errors)}",
        f"- **Revision Loops**: {rev_count}",
        f"- **Quality Score**: {quality.get('overall', 'N/A')}/10",
        f"- **Passes Quality Gate**: {quality.get('passes_gate', 'N/A')}",
        f"- **Output Formats**: LaTeX (`main.tex`), Markdown (`paper.md`), PDF",
        f"- **Total Generation Cost**: ${cost_summary.get('total_cost_usd', 0.0):.4f} USD",
        f"- **Total Tokens Consumed**: {cost_summary.get('total_tokens', 0):,}",
        "",
        "## Cost & Token Usage Analysis",
        "",
        f"- **Total Estimated Cost**: ${cost_summary.get('total_cost_usd', 0.0):.6f} USD",
        f"- **Prompt Tokens (Input)**: {cost_summary.get('total_input_tokens', 0):,}",
        f"- **Completion Tokens (Output)**: {cost_summary.get('total_output_tokens', 0):,}",
        f"- **Total Tokens**: {cost_summary.get('total_tokens', 0):,}",
        f"- **Total API Invocations**: {cost_summary.get('total_calls', 0)} "
        f"(LLM: {cost_summary.get('total_llm_calls', 0)}, "
        f"Images: {cost_summary.get('total_image_calls', 0)}, "
        f"Searches: {cost_summary.get('total_search_calls', 0)})",
        f"- **Total LLM Execution Latency**: {cost_summary.get('total_duration_seconds', 0.0)}s",
        "",
        "### Cost Breakdown by Model",
        "",
        "| Model / Service | Calls | Input Tokens | Output Tokens | Total Tokens | Cost (USD) |",
        "|---|---|---|---|---|---|",
    ]

    by_model = cost_summary.get("by_model", {})
    if by_model:
        for model_name, m_data in sorted(by_model.items(), key=lambda x: x[1].get("total_cost_usd", 0), reverse=True):
            report_lines.append(
                f"| `{model_name}` | {m_data.get('calls', 0)} | {m_data.get('input_tokens', 0):,} | "
                f"{m_data.get('output_tokens', 0):,} | {m_data.get('total_tokens', 0):,} | "
                f"${m_data.get('total_cost_usd', 0.0):.6f} |"
            )
    else:
        report_lines.append("| None | 0 | 0 | 0 | 0 | $0.000000 |")

    report_lines.extend([
        "",
        "### Cost Breakdown by Agent Node",
        "",
        "| Agent Node | Calls | Input Tokens | Output Tokens | Total Tokens | Cost (USD) |",
        "|---|---|---|---|---|---|",
    ])

    by_node = cost_summary.get("by_node", {})
    if by_node:
        for node_name, n_data in sorted(by_node.items(), key=lambda x: x[1].get("total_cost_usd", 0), reverse=True):
            report_lines.append(
                f"| `{node_name}` | {n_data.get('calls', 0)} | {n_data.get('input_tokens', 0):,} | "
                f"{n_data.get('output_tokens', 0):,} | {n_data.get('total_tokens', 0):,} | "
                f"${n_data.get('total_cost_usd', 0.0):.6f} |"
            )
    else:
        report_lines.append("| None | 0 | 0 | 0 | 0 | $0.000000 |")

    report_lines.extend([
        "",
        "## Quality Metrics",
        "",
        "| Dimension | Score |",
        "|---|---|",
    ])
    for dim in ["technical_accuracy", "novelty", "methodology_quality",
                "mathematical_rigor", "citation_quality", "coherence",
                "reproducibility", "publication_readiness"]:
        report_lines.append(f"| {dim.replace('_', ' ').title()} | {quality.get(dim, 'N/A')} |")

    report_lines.extend(["", "## Source Lineage", "",
                         f"- **Validated Sources**: {len(sources)}",
                         f"- **Rejected Sources**: {len(state.get('rejected_sources', []))}",
                         f"- **Evidence Chunks**: {len(state.get('evidence_chunks', []))}",
                         f"- **Citations Generated**: {state.get('citation_report', {}).get('total_citations', 0)}",
                         ""])

    report_lines.extend(["## Review History", ""])
    for fb in feedback:
        report_lines.append(
            f"- **{fb.get('reviewer_type', '').title()}**: score={fb.get('score', 'N/A')} "
            f"issues={len(fb.get('issues', []))} strengths={len(fb.get('strengths', []))}"
        )

    if errors:
        report_lines.extend(["", "## Error Report", ""])
        for err in errors[:20]:
            report_lines.append(f"- [{err.get('node', '')}] {err.get('error_class', '')}: "
                               f"{err.get('message', '')[:100]} (fallback: {err.get('fallback_used', '')})")

    report_lines.extend(["", "## Execution Log (last 30)", ""])
    for log in logs[-30:]:
        report_lines.append(f"- {log}")

    report = "\n".join(report_lines)

    # Write report and cost summary to disk
    try:
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, "traceability_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        get_current_tracker().export_json(os.path.join(output_dir, "cost_summary.json"))
    except Exception:
        pass

    return {
        "cost_summary": cost_summary,
        "traceability_report": report,
        "execution_log": [make_log_entry(node, "SUCCESS",
                          f"report_generated cost=${cost_summary.get('total_cost_usd', 0.0):.4f}")],
    }
