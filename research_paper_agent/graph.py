"""
Main Graph Assembly for Research Paper Agent.

Implements the complete 6-phase LangGraph StateGraph pipeline:
  Phase 1: Research Discovery (Planner → Parallel Lit Workers → Source Validator → Citation Miner → Evidence Extractor)
  Phase 2: Knowledge Synthesis (KG Builder → Domain Expert → Gap Analyzer [loop] → Hypothesis Generator → Novelty Evaluator [loop])
  Phase 3: Technical Design (Methodology Designer → Math Modeler → Experiment Designer → Data Analyst → Figure Planner)
  Phase 4: Drafting (Outline Generator → Parallel Section Writers → Content Aggregator → Citation Manager → Figure Generator)
  Phase 5: Review & Quality (Review Subgraph → Quality Gate → Revision Router [loop] → Parallel Section Writers)
  Phase 6: Compilation & Export (Publication Compiler → LaTeX Reviewer → Export Generator → Traceability Reporter → END)

Follows existing conventions from bwa_backend.py:
  - StateGraph(ResearchPaperState)
  - Send() for dynamic fan-out
  - Subgraph embedding via .compile()
  - Conditional edge routing with threshold & iteration guards
"""

from __future__ import annotations

from typing import List
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.config import (
    QUALITY_GATE_THRESHOLD,
    NOVELTY_THRESHOLD,
    MAX_REVISION_ITERATIONS,
    MAX_RESEARCH_ITERATIONS,
    MAX_NOVELTY_ITERATIONS,
    DEFAULT_SECTIONS,
)
from research_paper_agent.nodes import (
    research_planner_node,
    literature_worker_node,
    source_validator_node,
    citation_miner_node,
    evidence_extractor_node,
    knowledge_graph_builder_node,
    domain_expert_node,
    gap_analyzer_node,
    hypothesis_generator_node,
    novelty_evaluator_node,
    methodology_designer_node,
    math_modeler_node,
    experiment_designer_node,
    data_analyst_node,
    figure_planner_node,
    outline_generator_node,
    section_writer_node,
    content_aggregator_node,
    citation_manager_node,
    figure_generator_node,
    quality_gate_node,
    revision_router_node,
    master_orchestrator_init_node,
    master_orchestrator_review_node,
    publication_compiler_node,
    latex_reviewer_node,
    export_generator_node,
    traceability_reporter_node,
)
from research_paper_agent.subgraphs import review_subgraph


# ── Routing Functions ─────────────────────────────────────────────────

def route_after_gaps(state: ResearchPaperState) -> str:
    """Route after gap analysis: loop back to research planner or proceed."""
    severity = state.get("gap_severity", "none")
    iteration = state.get("research_iteration", 0)
    if severity == "critical" and iteration < MAX_RESEARCH_ITERATIONS:
        return "research_planner"
    return "hypothesis_generator"


def route_after_novelty(state: ResearchPaperState) -> str:
    """Route after novelty evaluation: loop back to hypothesis generator or proceed."""
    novelty = state.get("novelty_score", 10.0)
    iteration = state.get("novelty_iteration", 0)
    if novelty < NOVELTY_THRESHOLD and iteration < MAX_NOVELTY_ITERATIONS:
        return "hypothesis_generator"
    return "methodology_designer"


def route_after_quality(state: ResearchPaperState) -> str:
    """Route after quality gate: proceed to compiler or loop back for revisions."""
    scores = state.get("quality_scores") or {}
    overall = scores.get("overall", 0.0)
    rev = state.get("revision_count", 0)
    if overall >= QUALITY_GATE_THRESHOLD or rev >= MAX_REVISION_ITERATIONS:
        return "publication_compiler"
    return "revision_router"


def route_after_orchestrator_review(state: ResearchPaperState) -> str:
    """Route after Master Orchestrator review meta-evaluation."""
    directives = state.get("orchestrator_directives") or []
    if directives:
        latest = directives[-1]
        action = latest.get("action")
        if action == "proceed_to_publication":
            return "publication_compiler"
        return "revision_router"

    # Fallback to quality score check
    return route_after_quality(state)


# ── Fan-Out Functions (Send Pattern) ──────────────────────────────────

def literature_fanout(state: ResearchPaperState) -> List[Send]:
    """Fan out search queries to parallel literature workers."""
    queries = state.get("search_queries", [])
    if not queries:
        queries = [{"id": 1, "query_text": state.get("topic", "Research Topic")}]
    return [
        Send("literature_worker", {
            "query": q,
            "topic": state.get("topic", ""),
            "paper_type": state.get("paper_type", "technical"),
        })
        for q in queries
    ]


def section_fanout(state: ResearchPaperState) -> List[Send]:
    """Fan out section drafting tasks to parallel technical writers."""
    outline = state.get("paper_outline") or {}
    sections = outline.get("sections", [])
    if not sections:
        sections = [
            {
                "id": i,
                "title": s,
                "section_type": s.lower().replace(" ", "_"),
                "goal": f"Cover {s}",
                "key_points": ["Point 1", "Point 2", "Point 3"],
                "target_words": 500,
                "assigned_evidence_ids": [],
                "assigned_math_ids": [],
                "assigned_figure_ids": [],
                "requires_citations": True,
                "requires_methodology": False,
                "requires_math": False,
            }
            for i, s in enumerate(DEFAULT_SECTIONS)
        ]
    return [
        Send("section_writer", {
            "section_task": s,
            "paper_outline": outline,
            "evidence_chunks": state.get("evidence_chunks", []),
            "math_artifacts": state.get("math_artifacts", []),
            "methodology": state.get("methodology"),
            "figure_specs": state.get("figure_specs", []),
            "target_venue": state.get("target_venue", "arxiv"),
        })
        for s in sections
    ]


def revision_fanout(state: ResearchPaperState) -> List[Send]:
    """Fan out targeted section revision tasks to technical writers."""
    sections_to_revise = set(state.get("sections_to_revise", []))
    outline = state.get("paper_outline") or {}
    all_sections = outline.get("sections", [])
    directive = state.get("revision_directive") or {}
    notes_map = directive.get("revision_notes", {}) if isinstance(directive, dict) else {}

    if not sections_to_revise:
        sections_to_revise = {s.get("id") for s in all_sections}

    revisions = []
    for s in all_sections:
        if s.get("id") in sections_to_revise:
            sid_str = str(s.get("id"))
            note = notes_map.get(sid_str, notes_map.get(s.get("id"), "Address review feedback and improve rigor."))
            revisions.append(Send("section_writer", {
                "section_task": s,
                "paper_outline": outline,
                "evidence_chunks": state.get("evidence_chunks", []),
                "math_artifacts": state.get("math_artifacts", []),
                "methodology": state.get("methodology"),
                "figure_specs": state.get("figure_specs", []),
                "target_venue": state.get("target_venue", "arxiv"),
                "revision_notes": note,
                "is_revision": True,
            }))
    return revisions


# ── Graph Construction ────────────────────────────────────────────────

def build_research_paper_graph() -> StateGraph:
    """Assemble and return the uncompiled StateGraph."""
    g = StateGraph(ResearchPaperState)

    # ── Phase 0: Master Orchestrator ──
    g.add_node("master_orchestrator_init", master_orchestrator_init_node)

    # ── Phase 1: Research Discovery ──
    g.add_node("research_planner", research_planner_node)
    g.add_node("literature_worker", literature_worker_node)
    g.add_node("source_validator", source_validator_node)
    g.add_node("citation_miner", citation_miner_node)
    g.add_node("evidence_extractor", evidence_extractor_node)

    # ── Phase 2: Knowledge Synthesis ──
    g.add_node("knowledge_graph_builder", knowledge_graph_builder_node)
    g.add_node("domain_expert", domain_expert_node)
    g.add_node("gap_analyzer", gap_analyzer_node)
    g.add_node("hypothesis_generator", hypothesis_generator_node)
    g.add_node("novelty_evaluator", novelty_evaluator_node)

    # ── Phase 3: Technical Design ──
    g.add_node("methodology_designer", methodology_designer_node)
    g.add_node("math_modeler", math_modeler_node)
    g.add_node("experiment_designer", experiment_designer_node)
    g.add_node("data_analyst", data_analyst_node)
    g.add_node("figure_planner", figure_planner_node)

    # ── Phase 4: Drafting ──
    g.add_node("outline_generator", outline_generator_node)
    g.add_node("section_writer", section_writer_node)
    g.add_node("content_aggregator", content_aggregator_node)
    g.add_node("citation_manager", citation_manager_node)
    g.add_node("figure_generator", figure_generator_node)

    # ── Phase 5: Review & Quality ──
    g.add_node("review", review_subgraph)
    g.add_node("quality_gate", quality_gate_node)
    g.add_node("master_orchestrator_review", master_orchestrator_review_node)
    g.add_node("revision_router", revision_router_node)

    # ── Phase 6: Compilation & Export ──
    g.add_node("publication_compiler", publication_compiler_node)
    g.add_node("latex_reviewer", latex_reviewer_node)
    g.add_node("export_generator", export_generator_node)
    g.add_node("traceability_reporter", traceability_reporter_node)

    # ═══════════════ EDGES ═══════════════

    # Phase 0 & Phase 1
    g.add_edge(START, "master_orchestrator_init")
    g.add_edge("master_orchestrator_init", "research_planner")
    g.add_conditional_edges("research_planner", literature_fanout, ["literature_worker"])
    g.add_edge("literature_worker", "source_validator")
    # Parallel fan-out to citation miner and evidence extractor
    g.add_edge("source_validator", "citation_miner")
    g.add_edge("source_validator", "evidence_extractor")
    # Fan-in to knowledge graph builder
    g.add_edge("citation_miner", "knowledge_graph_builder")
    g.add_edge("evidence_extractor", "knowledge_graph_builder")

    # Phase 2
    g.add_edge("knowledge_graph_builder", "domain_expert")
    g.add_edge("domain_expert", "gap_analyzer")
    g.add_conditional_edges("gap_analyzer", route_after_gaps, {
        "research_planner": "research_planner",
        "hypothesis_generator": "hypothesis_generator",
    })
    g.add_edge("hypothesis_generator", "novelty_evaluator")
    g.add_conditional_edges("novelty_evaluator", route_after_novelty, {
        "hypothesis_generator": "hypothesis_generator",
        "methodology_designer": "methodology_designer",
    })

    # Phase 3
    g.add_edge("methodology_designer", "math_modeler")
    g.add_edge("math_modeler", "experiment_designer")
    # Parallel fan-out to data analyst and figure planner
    g.add_edge("experiment_designer", "data_analyst")
    g.add_edge("experiment_designer", "figure_planner")
    # Fan-in to outline generator
    g.add_edge("data_analyst", "outline_generator")
    g.add_edge("figure_planner", "outline_generator")
    g.add_conditional_edges("outline_generator", section_fanout, ["section_writer"])
    g.add_edge("section_writer", "content_aggregator")
    g.add_edge("content_aggregator", "citation_manager")
    g.add_edge("citation_manager", "figure_generator")

    # Phase 5: Review with Master Orchestrator Meta-Review
    g.add_edge("figure_generator", "review")
    g.add_edge("review", "master_orchestrator_review")
    g.add_conditional_edges("master_orchestrator_review", route_after_orchestrator_review, {
        "revision_router": "revision_router",
        "publication_compiler": "publication_compiler",
    })
    g.add_conditional_edges("revision_router", revision_fanout, ["section_writer"])

    # Phase 6
    g.add_edge("publication_compiler", "latex_reviewer")
    g.add_edge("latex_reviewer", "export_generator")
    g.add_edge("export_generator", "traceability_reporter")
    g.add_edge("traceability_reporter", END)

    return g


# Compile the production app instance
research_paper_app = build_research_paper_graph().compile()

__all__ = [
    "build_research_paper_graph",
    "research_paper_app",
    "route_after_gaps",
    "route_after_novelty",
    "route_after_quality",
    "route_after_orchestrator_review",
    "literature_fanout",
    "section_fanout",
    "revision_fanout",
]
