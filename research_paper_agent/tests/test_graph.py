"""Tests for graph construction and routing functions."""

from research_paper_agent.graph import (
    build_research_paper_graph,
    research_paper_app,
    route_after_gaps,
    route_after_novelty,
    route_after_quality,
    literature_fanout,
    section_fanout,
    revision_fanout,
)
from research_paper_agent.backend import build_initial_state


def test_graph_compiles():
    g = build_research_paper_graph()
    compiled = g.compile()
    assert compiled is not None
    assert research_paper_app is not None


def test_routing_gaps():
    # Critical gaps with iter 0 -> loop to research_planner
    state_crit = build_initial_state("Topic")
    state_crit["gap_severity"] = "critical"
    state_crit["research_iteration"] = 0
    assert route_after_gaps(state_crit) == "research_planner"

    # Critical gaps with iter 2 (max exhausted) -> proceed to hypothesis_generator
    state_max = build_initial_state("Topic")
    state_max["gap_severity"] = "critical"
    state_max["research_iteration"] = 2
    assert route_after_gaps(state_max) == "hypothesis_generator"

    # Minor gaps -> proceed to hypothesis_generator
    state_minor = build_initial_state("Topic")
    state_minor["gap_severity"] = "minor"
    assert route_after_gaps(state_minor) == "hypothesis_generator"


def test_routing_novelty():
    # Low novelty (< 5.0) with iter 0 -> loop to hypothesis_generator
    state_low = build_initial_state("Topic")
    state_low["novelty_score"] = 3.5
    state_low["novelty_iteration"] = 0
    assert route_after_novelty(state_low) == "hypothesis_generator"

    # High novelty (>= 5.0) -> proceed to methodology_designer
    state_high = build_initial_state("Topic")
    state_high["novelty_score"] = 7.5
    assert route_after_novelty(state_high) == "methodology_designer"


def test_routing_quality():
    # Passing quality (>= 7.0) -> publication_compiler
    state_pass = build_initial_state("Topic")
    state_pass["quality_scores"] = {"overall": 8.0, "passes_gate": True}
    assert route_after_quality(state_pass) == "publication_compiler"

    # Failing quality with revisions remaining -> revision_router
    state_fail = build_initial_state("Topic")
    state_fail["quality_scores"] = {"overall": 5.5, "passes_gate": False}
    state_fail["revision_count"] = 0
    assert route_after_quality(state_fail) == "revision_router"

    # Failing quality with max revisions exhausted -> publication_compiler (proceeds with degraded draft)
    state_exhaust = build_initial_state("Topic")
    state_exhaust["quality_scores"] = {"overall": 5.5, "passes_gate": False}
    state_exhaust["revision_count"] = 2
    assert route_after_quality(state_exhaust) == "publication_compiler"


def test_fanouts():
    state = build_initial_state("Transformers")
    state["search_queries"] = [{"id": 1, "query_text": "Attention"}]
    lit_sends = literature_fanout(state)
    assert len(lit_sends) == 1
    assert lit_sends[0].node == "literature_worker"

    state["paper_outline"] = {
        "paper_title": "Test Paper",
        "sections": [{"id": 1, "title": "Intro"}, {"id": 2, "title": "Methods"}],
    }
    sec_sends = section_fanout(state)
    assert len(sec_sends) == 2
    assert sec_sends[0].node == "section_writer"

    state["sections_to_revise"] = [2]
    rev_sends = revision_fanout(state)
    assert len(rev_sends) == 1
    assert rev_sends[0].node == "section_writer"
