"""
Central graph state definition.

Follows the existing convention exactly:
    class State(TypedDict):  with  Annotated[List, operator.add]
(bwa_backend.py L88-111)
"""

from __future__ import annotations

import operator
from typing import Annotated, List, Optional, TypedDict

__all__ = ["ResearchPaperState"]


class ResearchPaperState(TypedDict):
    # ── User Input ──
    topic: str
    paper_type: str                                          # technical | survey | review | position | case_study
    target_venue: str                                        # ieee_conference | acm | springer_lncs | arxiv | ...
    user_preferences: dict                                   # audience, depth, constraints

    # ── Master Orchestrator & Pre-Flight HITL ──
    pre_flight_estimate: Optional[dict]                      # PreFlightEstimate.model_dump()
    human_approved: bool                                     # True if user confirmed or auto-approved
    compact_mode: bool                                       # True if budget/fast compact mode
    orchestrator_strategy: Optional[dict]                    # OrchestratorStrategy.model_dump()
    orchestrator_directives: Annotated[List[dict], operator.add]  # List[OrchestratorDirective.model_dump()]

    # ── Research Planning ──
    research_plan: Optional[dict]                            # ResearchPlan.model_dump()
    search_queries: List[dict]                               # List[SearchQuery.model_dump()]

    # ── Literature Discovery (parallel fan-in) ──
    raw_literature: Annotated[List[dict], operator.add]

    # ── Source Validation ──
    validated_sources: List[dict]
    rejected_sources: List[dict]

    # ── Citation Mining ──
    citation_graph: List[dict]

    # ── Evidence Extraction ──
    evidence_chunks: List[dict]

    # ── Knowledge Graph ──
    knowledge_graph: dict                                    # {nodes, edges, clusters}

    # ── Domain Analysis ──
    domain_analysis: Optional[dict]

    # ── Gap Analysis ──
    research_gaps: List[dict]
    gap_severity: str                                        # critical | moderate | minor | none
    research_iteration: int

    # ── Hypothesis Generation ──
    hypotheses: List[dict]
    selected_hypothesis: Optional[dict]

    # ── Novelty Evaluation ──
    novelty_score: float
    novelty_assessment: Optional[dict]
    novelty_iteration: int

    # ── Methodology ──
    methodology: Optional[dict]

    # ── Mathematical Modeling ──
    math_artifacts: List[dict]

    # ── Experiment Design ──
    experiment_design: Optional[dict]

    # ── Data Analysis ──
    analysis_results: Optional[dict]

    # ── Figure Planning ──
    figure_specs: List[dict]

    # ── Paper Outline ──
    paper_outline: Optional[dict]

    # ── Section Drafting (parallel fan-in) ──
    drafted_sections: Annotated[List[tuple[int, str]], operator.add]

    # ── Content Aggregation ──
    merged_paper_tex: str

    # ── Citation Management ──
    bib_entries: List[dict]
    references_bib: str
    citation_report: Optional[dict]

    # ── Figure Generation ──
    generated_figures: List[dict]

    # ── Review (parallel fan-in from review subgraph) ──
    review_feedback: Annotated[List[dict], operator.add]
    quality_scores: Optional[dict]

    # ── Revision ──
    revision_count: int
    revision_directive: Optional[dict]
    sections_to_revise: List[int]

    # ── LaTeX Compilation ──
    latex_document: str
    latex_valid: bool
    latex_errors: List[str]

    # ── Final Output ──
    final_tex: str
    final_bib: str
    final_pdf_path: str
    final_markdown: str                                      # Complete paper formatted in Markdown
    final_markdown_path: str                                 # Path to generated paper.md
    output_dir: str

    # ── Traceability ──
    traceability_report: str

    # ── Cost & Token Tracking ──
    cost_summary: Optional[dict]                             # Overall token counts & USD cost breakdown
    llm_call_metrics: Annotated[List[dict], operator.add]   # Individual call records

    # ── Metadata & Error Tracking ──
    errors: Annotated[List[dict], operator.add]
    execution_log: Annotated[List[str], operator.add]
    as_of: str
