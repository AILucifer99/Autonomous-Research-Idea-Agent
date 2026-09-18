"""
Unit and integration tests for Master Orchestrator, Orchestrator Guide, and Pre-Flight HITL Logic.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from research_paper_agent.backend import build_initial_state
from research_paper_agent.config import MAX_UNCONFIRMED_API_CALLS, QUALITY_GATE_THRESHOLD
from research_paper_agent.graph import route_after_orchestrator_review
from research_paper_agent.nodes.master_orchestrator import (
    master_orchestrator_init_node,
    master_orchestrator_review_node,
)
from research_paper_agent.orchestrator_guide import (
    VENUE_STANDARDS,
    compute_preflight_estimate,
    get_venue_profile,
)
from research_paper_agent.schemas.orchestrator import (
    OrchestratorDirective,
    OrchestratorStrategy,
    PreFlightEstimate,
    VenueProfile,
)


def test_venue_profile_resolution():
    """Verify known venues resolve correctly and unknown venues produce a valid fallback."""
    ieee = get_venue_profile("ieee_conference")
    assert ieee.venue_key == "ieee_conference"
    assert "IEEE" in ieee.display_name
    assert ieee.target_word_count == 5500
    assert len(ieee.recommended_sections) > 0

    nature = get_venue_profile("nature")
    assert nature.venue_key == "nature"
    assert nature.math_depth == "applied"
    assert nature.target_word_count == 4500

    # Fallback resolution
    custom = get_venue_profile("neurips_workshop_2026")
    assert custom is not None
    assert custom.venue_key == "neurips_workshop_2026"
    assert custom.target_word_count > 0


def test_compute_preflight_estimate_normal():
    """Verify pre-flight estimation calculates calls, tokens, costs, and triggers confirmation."""
    estimate = compute_preflight_estimate(
        topic="Diffusion Models for Scientific Discovery",
        paper_type="technical",
        target_venue="ieee_conference",
        user_preferences={"audience": "researchers"},
        compact_mode=False,
    )

    assert isinstance(estimate, PreFlightEstimate)
    total_calls = estimate.estimated_llm_calls + estimate.estimated_search_queries + estimate.estimated_image_calls
    assert total_calls > MAX_UNCONFIRMED_API_CALLS
    assert estimate.requires_human_confirmation is True
    assert len(estimate.reasons_for_confirmation) > 0
    assert estimate.estimated_cost_usd > 0.0
    assert estimate.estimated_total_tokens > 50_000


def test_compute_preflight_estimate_compact_mode():
    """Verify compact mode reduces estimated calls, tokens, and duration."""
    normal = compute_preflight_estimate("Topic", compact_mode=False)
    compact = compute_preflight_estimate("Topic", compact_mode=True)

    normal_calls = normal.estimated_llm_calls + normal.estimated_search_queries + normal.estimated_image_calls
    compact_calls = compact.estimated_llm_calls + compact.estimated_search_queries + compact.estimated_image_calls

    assert compact_calls < normal_calls
    assert compact.estimated_total_tokens < normal.estimated_total_tokens
    assert compact.estimated_cost_usd <= normal.estimated_cost_usd
    assert compact.estimated_duration_seconds < normal.estimated_duration_seconds


def test_master_orchestrator_init_fallback():
    """Verify master_orchestrator_init gracefully falls back to venue defaults on LLM exception."""
    state = build_initial_state("Reinforcement Learning from Human Feedback", target_venue="acm")
    
    with patch("research_paper_agent.nodes.master_orchestrator.llm_strong") as mock_llm:
        mock_llm.invoke.side_effect = RuntimeError("API offline")
        update = master_orchestrator_init_node(state)

    assert "orchestrator_strategy" in update
    strat = update["orchestrator_strategy"]
    assert strat["venue_profile"]["venue_key"] == "acm"
    assert strat["target_figure_count"] == 5
    assert len(strat["core_focus_areas"]) > 0
    assert any("DEGRADED" in log for log in update.get("execution_log", []))


def test_master_orchestrator_init_list_content():
    """Verify master_orchestrator_init cleanly handles list-of-dicts content from Gemini SDK."""
    state = build_initial_state("Self-Supervised Representation Learning for Graphs", target_venue="ieee_conference")
    
    mock_resp = MagicMock()
    mock_resp.content = [
        {"text": '```json\n{"strategic_guidance": "Focus on GNN contrastive objectives", "core_focus_areas": ["GNN", "SSL"], "word_budget_allocation": {"Abstract": 250}, "target_figure_count": 2}\n```'}
    ]
    
    with patch("research_paper_agent.nodes.master_orchestrator.llm_strong") as mock_llm:
        mock_llm.invoke.return_value = mock_resp
        update = master_orchestrator_init_node(state)
        
    assert "orchestrator_strategy" in update
    strat = update["orchestrator_strategy"]
    assert strat["target_figure_count"] == 2
    assert "GNN" in strat["core_focus_areas"]
    assert "SUCCESS" in update["execution_log"][0]


def test_master_orchestrator_review_pass():
    """Verify area chair approves publication when scores meet or exceed threshold."""
    state = build_initial_state("Graph Transformers", target_venue="arxiv")
    state["quality_scores"] = {
        "technical_depth": 8.5,
        "academic_coherence": 8.5,
        "citation_integrity": 8.0,
        "novelty": 8.0,
        "structure_and_format": 8.0,
        "overall": 8.2,
    }
    state["revision_count"] = 0

    mock_resp = MagicMock()
    mock_resp.content = '{"action": "proceed_to_publication", "composite_score": 8.2, "target_sections": [], "instructions": "Paper is ready.", "reasoning": "High quality."}'

    with patch("research_paper_agent.nodes.master_orchestrator.llm_strong") as mock_llm:
        mock_llm.invoke.return_value = mock_resp
        update = master_orchestrator_review_node(state)

    directive = update["orchestrator_directives"][0]
    assert directive["action"] == "proceed_to_publication"
    assert update["sections_to_revise"] == []
    assert update["revision_count"] == 0


def test_master_orchestrator_review_revise():
    """Verify area chair issues revision directives when scores are below threshold."""
    state = build_initial_state("Quantum Neural Networks", target_venue="ieee_conference")
    state["quality_scores"] = {
        "technical_depth": 5.0,
        "academic_coherence": 6.0,
        "citation_integrity": 5.0,
        "novelty": 6.0,
        "structure_and_format": 6.0,
        "overall": 5.6,
    }
    state["revision_count"] = 0

    mock_resp = MagicMock()
    mock_resp.content = '{"action": "revise_sections", "composite_score": 5.6, "target_sections": [2, 3], "instructions": "Deepen mathematical rigor in Methodology.", "reasoning": "Equations need proof."}'

    with patch("research_paper_agent.nodes.master_orchestrator.llm_strong") as mock_llm:
        mock_llm.invoke.return_value = mock_resp
        update = master_orchestrator_review_node(state)

    directive = update["orchestrator_directives"][0]
    assert directive["action"] == "revise_sections"
    assert update["sections_to_revise"] == [2, 3]
    assert update["revision_count"] == 1


def test_master_orchestrator_review_max_iterations():
    """Verify area chair forces publication when max revision limit is reached."""
    state = build_initial_state("Edge Computing AI", target_venue="elsevier")
    state["quality_scores"] = {"overall": 5.0}
    state["revision_count"] = 2  # Max iterations exhausted

    update = master_orchestrator_review_node(state)

    directive = update["orchestrator_directives"][0]
    assert directive["action"] == "proceed_to_publication"
    assert update["sections_to_revise"] == []


def test_route_after_orchestrator_review():
    """Verify graph routing correctly interprets orchestrator directives."""
    # Action = proceed_to_publication
    state_pass = build_initial_state("Topic")
    state_pass["orchestrator_directives"] = [{"action": "proceed_to_publication"}]
    assert route_after_orchestrator_review(state_pass) == "publication_compiler"

    # Action = revise_sections
    state_revise = build_initial_state("Topic")
    state_revise["orchestrator_directives"] = [{"action": "revise_sections"}]
    assert route_after_orchestrator_review(state_revise) == "revision_router"
