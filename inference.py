"""
Autonomous Research Paper Agent — Advanced CLI & Programmatic Inference.

Allows invoking the multi-agent research pipeline with custom topics,
venue templates, paper types, and user preferences with real-time rich streaming,
markdown document output, granular figure handling, and live cost tracking.

Usage Examples:
    # Basic technical paper on ArXiv (streaming progress)
    python inference.py --topic "Mechanistic Interpretability in Large Language Models"

    # Survey paper targeting an IEEE Conference
    python inference.py --topic "State Space Models vs Transformers" --paper-type survey --target-venue ieee_conference

    # Synchronous execution with custom audience and zip bundling
    python inference.py --topic "Neural Ordinary Differential Equations" --audience "PhD researchers" --no-stream --zip
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure standard output uses UTF-8 with safe fallback on Windows
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv

# Ensure local environment variables are loaded
load_dotenv()

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from research_paper_agent.backend import (
    bundle_paper_zip,
    run_pipeline,
    safe_slug,
    stream_pipeline,
)
from research_paper_agent.config import PAPER_TYPES, TARGET_VENUES
from research_paper_agent.orchestrator_guide import compute_preflight_estimate, get_venue_profile
from research_paper_agent.schemas.orchestrator import PreFlightEstimate

console = Console(safe_box=True)

PHASE_BADGES: Dict[str, tuple[str, str]] = {
    "master_orchestrator_init": ("PHASE 0", "Master Orchestrator"),
    "research_planner": ("PHASE 1", "Research Discovery"),
    "literature_worker": ("PHASE 1", "Literature Worker"),
    "source_validator": ("PHASE 1", "Source Validation"),
    "citation_miner": ("PHASE 1", "Citation Miner"),
    "evidence_extractor": ("PHASE 1", "Evidence Extractor"),
    "knowledge_graph_builder": ("PHASE 2", "Knowledge Graph"),
    "domain_expert": ("PHASE 2", "Domain Analysis"),
    "gap_analyzer": ("PHASE 2", "Gap Analysis"),
    "hypothesis_generator": ("PHASE 2", "Hypothesis Gen"),
    "novelty_evaluator": ("PHASE 2", "Novelty Evaluator"),
    "methodology_designer": ("PHASE 3", "Methodology Design"),
    "math_modeler": ("PHASE 3", "Math Modeling"),
    "experiment_designer": ("PHASE 3", "Experiment Design"),
    "data_analyst": ("PHASE 3", "Data Analysis"),
    "figure_planner": ("PHASE 3", "Figure Planning"),
    "outline_generator": ("PHASE 4", "Outline Generator"),
    "section_writer": ("PHASE 4", "Section Writer"),
    "content_aggregator": ("PHASE 4", "Content Aggregator"),
    "citation_manager": ("PHASE 4", "Citation Manager"),
    "figure_generator": ("PHASE 4", "Figure Generator"),
    "review": ("PHASE 5", "Parallel Reviewers"),
    "scientific_reviewer": ("PHASE 5", "Scientific Review"),
    "fact_verifier": ("PHASE 5", "Fact Verification"),
    "consistency_validator": ("PHASE 5", "Consistency Check"),
    "statistical_reviewer": ("PHASE 5", "Statistical Review"),
    "reproducibility_reviewer": ("PHASE 5", "Reproducibility Review"),
    "quality_assessor": ("PHASE 5", "Quality Assessor"),
    "master_orchestrator_review": ("PHASE 5", "Area Chair Meta-Review"),
    "quality_gate": ("PHASE 5", "Quality Gate"),
    "revision_router": ("PHASE 5", "Revision Router"),
    "publication_compiler": ("PHASE 6", "Publication Compiler"),
    "latex_reviewer": ("PHASE 6", "LaTeX Reviewer"),
    "export_generator": ("PHASE 6", "Export & Markdown"),
    "traceability_reporter": ("PHASE 6", "Traceability Reporter"),
}


def print_banner() -> None:
    title_text = Text("AUTONOMOUS RESEARCH PAPER AGENT", style="bold cyan")
    subtitle_text = Text(
        "Multi-Agent LangGraph Scientific Authoring & Optimization Framework\n"
        "Google Gemini 2.5/3.5 • Tavily Search • LaTeX & Markdown Export • Cost Tracking",
        style="dim white",
    )
    panel = Panel(
        Text.assemble(title_text, "\n", subtitle_text),
        box=box.DOUBLE_EDGE,
        border_style="bright_blue",
        padding=(1, 2),
    )
    console.print(panel)


def check_environment() -> bool:
    """Verify required API keys are configured."""
    has_google = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
    has_tavily = bool(os.getenv("TAVILY_API_KEY"))

    if not has_google:
        console.print(
            Panel(
                "[bold red]MISSING REQUIRED API KEY[/bold red]\n\n"
                "Neither [yellow]GOOGLE_API_KEY[/yellow] nor [yellow]GEMINI_API_KEY[/yellow] was detected.\n"
                "Please add your Gemini key to the [bold].env[/bold] file before running.",
                title="Configuration Error",
                border_style="red",
            )
        )
        return False

    env_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    env_table.add_column("Key", style="bold white")
    env_table.add_column("Status", style="green")

    env_table.add_row("Google GenAI API", "[bold green]✓ Configured[/bold green]")
    if has_tavily:
        env_table.add_row("Tavily Search API", "[bold green]✓ Configured[/bold green]")
    else:
        env_table.add_row("Tavily Search API", "[bold yellow]⚠ Missing (using academic fallback queries)[/bold yellow]")

    console.print(env_table)
    return True


def request_preflight_authorization(
    estimate: PreFlightEstimate,
    auto_approve: bool = False,
) -> tuple[bool, bool]:
    """
    Renders the HITL Pre-Flight Resource & Cost Authorization panel.
    Returns (proceed: bool, compact_mode: bool).
    """
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Metric", style="dim cyan")
    table.add_column("Value", style="bold bright_white")

    tot_calls = estimate.estimated_llm_calls + estimate.estimated_search_queries + estimate.estimated_image_calls
    table.add_row("Estimated Total API Calls", f"[bold yellow]{tot_calls}[/bold yellow] calls")
    table.add_row("  ↳ LLM Agents", f"{estimate.estimated_llm_calls} calls")
    table.add_row("  ↳ Tavily Searches", f"{estimate.estimated_search_queries} queries")
    table.add_row("  ↳ Gemini Figures", f"{estimate.estimated_image_calls} images")
    table.add_row("Estimated Token Volume", f"{estimate.estimated_total_tokens:,} tokens")
    table.add_row("Estimated Cost (USD)", f"[bold bright_green]${estimate.estimated_cost_usd:.4f}[/bold bright_green]")
    table.add_row("Estimated Wall Clock", f"~{estimate.estimated_duration_seconds}s")

    panel = Panel(
        table,
        title="[bold bright_yellow]⚠ Human-in-the-Loop Pre-Flight Authorization Required[/bold bright_yellow]",
        subtitle=f"[dim]Auto-approve: {auto_approve}[/dim]",
        border_style="yellow",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print(panel)

    if estimate.reasons_for_confirmation:
        reasons_text = "\n".join(f" • [white]{r}[/white]" for r in estimate.reasons_for_confirmation)
        console.print(Panel(reasons_text, title="[yellow]Trigger Safeguard Criteria[/yellow]", box=box.SIMPLE, border_style="dim yellow"))

    if auto_approve:
        console.print("[bold green]✔ Auto-approve active (--auto-approve). Proceeding automatically.[/bold green]\n")
        return True, False

    console.print(
        "\n[bold bright_white]Human-in-the-Loop Options:[/bold bright_white]\n"
        " • [bold green][Y][/bold green] Proceed with complete high-rigor research generation\n"
        " • [bold cyan][C][/bold cyan] Switch to [bold]Compact Mode[/bold] (scales down calls & cost ~40%)\n"
        " • [bold red][N][/bold red] Cancel execution\n"
    )

    try:
        choice = console.input("[bold yellow]Authorize execution? [Y/c/n] (default: Y): [/bold yellow]").strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print("\n[bold red]Cancelled by user.[/bold red]")
        return False, False

    if choice in ("c", "compact"):
        console.print("[bold cyan]✔ Compact Mode selected! Scaling down outline targets and queries.[/bold cyan]\n")
        return True, True
    elif choice in ("n", "no", "abort", "cancel"):
        console.print("[bold red]✖ Execution aborted by user.[/bold red]\n")
        return False, False
    else:
        console.print("[bold green]✔ High-Rigor Generation authorized! Initiating pipeline...[/bold green]\n")
        return True, False


def display_configuration(
    topic: str,
    paper_type: str,
    target_venue: str,
    audience: str,
    depth: str,
    stream: bool,
    create_zip: bool,
    compact_mode: bool = False,
    estimated_cost: float = 0.0,
) -> None:
    table = Table(title="Pipeline Execution Configuration", box=box.ROUNDED, border_style="cyan")
    table.add_column("Parameter", style="bold bright_white", width=24)
    table.add_column("Value", style="bright_cyan")

    table.add_row("Research Topic", f"[bold]{topic}[/bold]")
    table.add_row("Paper Type", f"[magenta]{paper_type}[/magenta]")
    table.add_row("Target Venue Template", f"[blue]{target_venue}[/blue]")
    table.add_row("Target Audience", audience)
    table.add_row("Analytical Depth", depth.capitalize())
    table.add_row("Execution Strategy", "[bold yellow]Compact Mode (Fast/Budget)[/bold yellow]" if compact_mode else "[green]Comprehensive Academic High-Rigor[/green]")
    table.add_row("Pre-Flight Est. Cost", f"[bold green]${estimated_cost:.4f} USD[/bold green]")
    table.add_row("Execution Mode", "[green]Streaming (Real-time updates)[/green]" if stream else "[dim]Batch Synchronous[/dim]")
    table.add_row("ZIP Packaging", "[green]Enabled[/green]" if create_zip else "[dim]Disabled[/dim]")

    console.print(table)


def display_artifacts(final_state: Dict[str, Any], output_dir: str, create_zip: bool) -> None:
    tex_path = Path(output_dir) / "main.tex"
    bib_path = Path(output_dir) / "references.bib"
    pdf_path = final_state.get("final_pdf_path")
    md_path = Path(output_dir) / "paper.md"
    report_path = Path(output_dir) / "traceability_report.md"
    cost_path = Path(output_dir) / "cost_summary.json"

    table = Table(title="Generated Research Deliverables", box=box.ROUNDED, border_style="bright_green")
    table.add_column("Artifact", style="bold white", width=24)
    table.add_column("Format", style="cyan", width=12)
    table.add_column("Path / Status", style="bright_white")

    # Final Markdown Paper (Prominently Highlighted)
    if md_path.exists():
        table.add_row(
            "[bold green]Markdown Manuscript[/bold green]",
            "[bold green]Markdown (.md)[/bold green]",
            f"[bold underline green]{md_path.resolve()}[/bold underline green]",
        )
    else:
        table.add_row("Markdown Manuscript", "Markdown (.md)", "[yellow]Pending[/yellow]")

    # LaTeX Manuscript
    if tex_path.exists():
        table.add_row("LaTeX Source", "LaTeX (.tex)", str(tex_path.resolve()))
    if bib_path.exists():
        table.add_row("Bibliography", "BibTeX (.bib)", str(bib_path.resolve()))

    # PDF Document
    if pdf_path and Path(pdf_path).exists():
        table.add_row("[bold bright_magenta]Compiled PDF[/bold bright_magenta]", "PDF (.pdf)", str(Path(pdf_path).resolve()))
    else:
        table.add_row("Compiled PDF", "PDF (.pdf)", "[dim]TeX bundle available for local/Overleaf compilation[/dim]")

    # Figures count
    figures = final_state.get("generated_figures", [])
    succ_figs = [f for f in figures if f.get("success")]
    if succ_figs:
        table.add_row("Generated Figures", "PNG / TikZ", f"[green]{len(succ_figs)} figures created[/green] in figures/")

    # Traceability & Cost Reports
    if report_path.exists():
        table.add_row("Traceability Report", "Markdown (.md)", str(report_path.resolve()))
    if cost_path.exists():
        table.add_row("Cost Summary Audit", "JSON (.json)", str(cost_path.resolve()))

    # Bundle ZIP
    if create_zip and Path(output_dir).exists():
        zip_bytes = bundle_paper_zip(output_dir)
        if zip_bytes:
            zip_dest = Path(output_dir).parent / f"{Path(output_dir).name}_bundle.zip"
            zip_dest.write_bytes(zip_bytes)
            table.add_row("[bold yellow]Deployable ZIP Archive[/bold yellow]", "ZIP (.zip)", f"[bold yellow]{zip_dest.resolve()}[/bold yellow]")

    console.print(table)


def display_quality_metrics(quality: Dict[str, Any]) -> None:
    if not quality:
        return

    table = Table(title="Academic Quality Evaluation", box=box.ROUNDED, border_style="bright_magenta")
    table.add_column("Evaluation Dimension", style="bold white", width=28)
    table.add_column("Score (0-10)", style="cyan", justify="center", width=14)
    table.add_column("Assessment Rating", style="bright_white")

    dimensions = [
        ("technical_accuracy", "Technical Accuracy"),
        ("novelty", "Hypothesis Novelty"),
        ("methodology_quality", "Methodology Rigor"),
        ("mathematical_rigor", "Mathematical Rigor"),
        ("citation_quality", "Citation Integrity"),
        ("coherence", "Structural Coherence"),
        ("reproducibility", "Reproducibility"),
        ("publication_readiness", "Publication Readiness"),
    ]

    for key, label in dimensions:
        score = quality.get(key, 0.0)
        color = "green" if score >= 7.5 else ("yellow" if score >= 5.5 else "red")
        stars = "★" * int(round(score / 2)) + "☆" * (5 - int(round(score / 2)))
        table.add_row(label, f"[{color}]{score:.1f} / 10[/{color}]", f"[{color}]{stars}[/{color}]")

    overall = quality.get("overall", 0.0)
    passes = quality.get("passes_gate", False)
    gate_badge = "[bold green]PASSES QUALITY GATE[/bold green]" if passes else "[bold red]FAILED QUALITY GATE[/bold red]"
    table.add_section()
    table.add_row("[bold white]Composite Overall Score[/bold white]", f"[bold bright_green]{overall:.2f} / 10[/bold bright_green]", gate_badge)

    console.print(table)


def display_cost_tables(cost_summary: Dict[str, Any]) -> None:
    if not cost_summary:
        return

    total_cost = cost_summary.get("total_cost_usd", 0.0)
    total_in = cost_summary.get("total_input_tokens", 0)
    total_out = cost_summary.get("total_output_tokens", 0)
    total_tok = cost_summary.get("total_tokens", 0)
    total_calls = cost_summary.get("total_calls", 0)
    duration = cost_summary.get("total_duration_seconds", 0.0)

    # Cost Summary Overview Panel
    summary_panel = Panel(
        Text.assemble(
            ("Total Generation Cost : ", "bold white"),
            (f"${total_cost:.6f} USD\n", "bold bright_green"),
            ("Total Token Volume    : ", "bold white"),
            (f"{total_tok:,} tokens ", "bright_cyan"),
            (f"(Prompt: {total_in:,} | Completion: {total_out:,})\n", "dim white"),
            ("Total API Invocations : ", "bold white"),
            (f"{total_calls} calls ", "bright_yellow"),
            (f"(Duration: {duration:.2f}s)", "dim white"),
        ),
        title="Token & Cost Consumption Analysis",
        box=box.ROUNDED,
        border_style="bright_yellow",
    )
    console.print(summary_panel)

    # Model Breakdown Table
    by_model = cost_summary.get("by_model", {})
    if by_model:
        model_table = Table(title="Cost Breakdown by LLM & Tool Service", box=box.ROUNDED, border_style="yellow")
        model_table.add_column("Model / Service", style="bold bright_white")
        model_table.add_column("Calls", justify="center", style="cyan")
        model_table.add_column("Input Tokens", justify="right", style="dim white")
        model_table.add_column("Output Tokens", justify="right", style="dim white")
        model_table.add_column("Total Tokens", justify="right", style="bright_cyan")
        model_table.add_column("Cost (USD)", justify="right", style="bold bright_green")

        for model, data in sorted(by_model.items(), key=lambda x: x[1].get("total_cost_usd", 0), reverse=True):
            model_table.add_row(
                model,
                str(data.get("calls", 0)),
                f"{data.get('input_tokens', 0):,}",
                f"{data.get('output_tokens', 0):,}",
                f"{data.get('total_tokens', 0):,}",
                f"${data.get('total_cost_usd', 0.0):.6f}",
            )
        console.print(model_table)

    # Node Breakdown Table
    by_node = cost_summary.get("by_node", {})
    if by_node:
        node_table = Table(title="Cost Breakdown by Agent Node", box=box.ROUNDED, border_style="blue")
        node_table.add_column("Agent Node", style="bold bright_white")
        node_table.add_column("Calls", justify="center", style="cyan")
        node_table.add_column("Total Tokens", justify="right", style="bright_cyan")
        node_table.add_column("Cost (USD)", justify="right", style="bold bright_green")

        for node_name, data in sorted(by_node.items(), key=lambda x: x[1].get("total_cost_usd", 0), reverse=True):
            node_table.add_row(
                node_name,
                str(data.get("calls", 0)),
                f"{data.get('total_tokens', 0):,}",
                f"${data.get('total_cost_usd', 0.0):.6f}",
            )
        console.print(node_table)


def run_inference(
    topic: str,
    paper_type: str = "technical",
    target_venue: str = "arxiv",
    audience: str = "researchers",
    depth: str = "deep",
    custom_constraints: Optional[str] = None,
    stream: bool = True,
    create_zip: bool = True,
    compact: bool = False,
    auto_approve: bool = False,
) -> Dict[str, Any]:
    """
    Programmatic entrypoint to generate a research paper with Master Orchestrator
    and Pre-Flight HITL authorization.
    """
    user_preferences = {
        "audience": audience,
        "depth": depth,
    }
    if custom_constraints:
        user_preferences["constraints"] = custom_constraints

    # 1. Upfront Pre-Flight Resource & Cost Estimation
    estimate = compute_preflight_estimate(
        topic=topic,
        paper_type=paper_type,
        target_venue=target_venue,
        user_preferences=user_preferences,
        compact_mode=compact,
    )

    # 2. Human-in-the-Loop Pre-Flight Authorization Gate
    compact_mode = compact
    if estimate.requires_human_confirmation and not auto_approve:
        authorized, compact_choice = request_preflight_authorization(
            estimate=estimate,
            auto_approve=auto_approve,
        )
        if not authorized:
            console.print("[bold yellow]Pipeline stopped before dispatching any API calls.[/bold yellow]")
            out_dir = os.path.join("output", safe_slug(topic))
            return {
                "aborted": True,
                "reason": "Pre-flight authorization cancelled by user",
                "output_dir": out_dir,
                "cost_summary": {"total_cost_usd": 0.0, "total_calls": 0, "total_tokens": 0},
                "quality_scores": {},
                "final_tex": "",
                "final_pdf_path": "",
                "final_markdown": "",
            }
        if compact_choice:
            compact_mode = True
            # Recompute estimate under compact mode parameters
            estimate = compute_preflight_estimate(
                topic=topic,
                paper_type=paper_type,
                target_venue=target_venue,
                user_preferences=user_preferences,
                compact_mode=True,
            )

    display_configuration(
        topic=topic,
        paper_type=paper_type,
        target_venue=target_venue,
        audience=audience,
        depth=depth,
        stream=stream,
        create_zip=create_zip,
        compact_mode=compact_mode,
        estimated_cost=estimate.estimated_cost_usd,
    )

    start_time = time.time()
    final_state: Dict[str, Any] = {}

    if stream:
        console.print("\n[bold cyan]⚡ Initiating multi-agent execution pipeline...[/bold cyan]\n")
        completed_nodes = set()

        for event_type, payload in stream_pipeline(
            topic=topic,
            paper_type=paper_type,
            target_venue=target_venue,
            user_preferences=user_preferences,
            compact_mode=compact_mode,
            human_approved=True,
        ):
            if event_type == "updates" and isinstance(payload, dict):
                for node_name, state_update in payload.items():
                    phase_tag, phase_title = PHASE_BADGES.get(node_name, ("EXEC", "Pipeline Step"))
                    status_detail = ""
                    if isinstance(state_update, dict):
                        if "orchestrator_strategy" in state_update and state_update["orchestrator_strategy"]:
                            strat = state_update["orchestrator_strategy"]
                            vp = strat.get("venue_profile", {})
                            status_detail = f"[dim]venue={vp.get('venue_key', 'generic')}, target_words={vp.get('target_word_count')}, figs={strat.get('target_figure_count')}[/dim]"
                        elif "research_plan" in state_update and state_update["research_plan"]:
                            queries = state_update.get("search_queries", [])
                            status_detail = f"[dim]queries planned: {len(queries)}[/dim]"
                        elif "quality_scores" in state_update and state_update["quality_scores"]:
                            score = state_update["quality_scores"].get("overall", "N/A")
                            passes = state_update["quality_scores"].get("passes_gate", False)
                            status_detail = f"[bold]score={score}/10 (passes={passes})[/bold]"
                        elif "orchestrator_directives" in state_update and state_update["orchestrator_directives"]:
                            latest = state_update["orchestrator_directives"][-1]
                            action = latest.get("action", "")
                            comp_score = latest.get("composite_score", 0.0)
                            status_detail = f"[bold]action={action} (composite={comp_score:.2f}/10)[/bold]"
                        elif "figure_specs" in state_update:
                            figs = state_update.get("figure_specs", [])
                            status_detail = f"[dim]figures planned: {len(figs)}[/dim]"
                        elif "generated_figures" in state_update:
                            figs = state_update.get("generated_figures", [])
                            succ = sum(1 for f in figs if f.get("success"))
                            status_detail = f"[dim]generated {succ}/{len(figs)} figures[/dim]"
                        elif "latex_document" in state_update:
                            status_detail = "[dim]compiled LaTeX & markdown[/dim]"
                        elif "traceability_report" in state_update:
                            status_detail = "[dim]generated traceability audit[/dim]"

                    prefix = "[bold green]✓[/bold green]"
                    console.print(f"  {prefix} [{phase_tag}] [bold white]{node_name:<27}[/bold white] {status_detail}")
                    completed_nodes.add(node_name)

            elif event_type == "final":
                final_state = payload

    else:
        with console.status("[bold cyan]Running autonomous research pipeline...[/bold cyan]", spinner="dots12"):
            final_state = run_pipeline(
                topic=topic,
                paper_type=paper_type,
                target_venue=target_venue,
                user_preferences=user_preferences,
                compact_mode=compact_mode,
                human_approved=True,
            )

    elapsed = time.time() - start_time
    console.print(f"\n[bold green]✔ Research paper generation complete![/bold green] [dim](Elapsed: {elapsed:.2f}s)[/dim]\n")

    output_dir = final_state.get("output_dir", "output/paper")

    # Display Deliverables, Quality, and Costs with Rich
    display_artifacts(final_state, output_dir=output_dir, create_zip=create_zip)
    display_quality_metrics(final_state.get("quality_scores") or {})
    display_cost_tables(final_state.get("cost_summary") or {})

    return final_state


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autonomous Research Paper Agent — Advanced CLI Inference Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python inference.py --topic "Transformer Scaling Laws and Inference Optimization"
  python inference.py --topic "Self-Supervised Learning on Graph Neural Networks" --paper-type survey --target-venue acm
  python inference.py --topic "Quantum Machine Learning" --compact -y
        """,
    )

    parser.add_argument(
        "--topic",
        "-t",
        type=str,
        required=True,
        help="The research topic, research question, or working title of the paper.",
    )
    parser.add_argument(
        "--paper-type",
        "-p",
        type=str,
        default="technical",
        choices=PAPER_TYPES,
        help=f"Type of manuscript (default: technical). Choices: {', '.join(PAPER_TYPES)}",
    )
    parser.add_argument(
        "--target-venue",
        "-v",
        type=str,
        default="arxiv",
        choices=TARGET_VENUES,
        help=f"Target publication venue template (default: arxiv). Choices: {', '.join(TARGET_VENUES)}",
    )
    parser.add_argument(
        "--audience",
        "-a",
        type=str,
        default="researchers",
        help="Target audience level (e.g., 'researchers', 'engineers', 'academics').",
    )
    parser.add_argument(
        "--depth",
        "-d",
        type=str,
        default="deep",
        choices=["deep", "concise"],
        help="Depth level for literature analysis and technical detail (default: deep).",
    )
    parser.add_argument(
        "--constraints",
        "-c",
        type=str,
        default=None,
        help="Optional custom constraints or focus instructions for the agents.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        default=False,
        help="Run workflow in budget-friendly compact mode (reduces section targets, search queries, and figure generation).",
    )
    parser.add_argument(
        "--auto-approve",
        "-y",
        action="store_true",
        default=False,
        help="Automatically authorize pre-flight execution without interactive human-in-the-loop prompt.",
    )
    parser.add_argument(
        "--stream",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Stream pipeline updates node-by-node (default: --stream). Use --no-stream for quiet batch run.",
    )
    parser.add_argument(
        "--zip",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Automatically generate a ZIP archive of all outputs in the output folder (default: --zip).",
    )

    args = parser.parse_args()

    print_banner()
    if not check_environment():
        sys.exit(1)

    try:
        run_inference(
            topic=args.topic,
            paper_type=args.paper_type,
            target_venue=args.target_venue,
            audience=args.audience,
            depth=args.depth,
            custom_constraints=args.constraints,
            stream=args.stream,
            create_zip=args.zip,
            compact=args.compact,
            auto_approve=args.auto_approve,
        )
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]⚠️  Execution interrupted by user.[/bold yellow]")
        sys.exit(130)
    except Exception as exc:
        console.print(f"\n[bold red]❌ Pipeline execution failed:[/bold red] {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
