"""
Master Orchestrator Agent — Powered by Gemini LLM.

Acts as the Principal Investigator and Senior Area Chair:
1. `master_orchestrator_init_node`: Sets global strategy, venue rubrics, word budgets, and architectural focus.
2. `master_orchestrator_review_node`: Meta-evaluates multi-agent peer reviews against venue standards
   and issues targeted revision directives or approves publication.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from research_paper_agent.config import (
    MAX_REVISION_ITERATIONS,
    ORCHESTRATOR_CONFIG,
    QUALITY_GATE_THRESHOLD,
    SECTION_WORD_RANGES,
)
from research_paper_agent.errors import make_error_entry, make_log_entry
from research_paper_agent.llm import extract_text_content, llm_strong
from research_paper_agent.orchestrator_guide import (
    VENUE_STANDARDS,
    build_orchestrator_initial_prompt,
    build_orchestrator_meta_review_prompt,
    get_venue_profile,
)
from research_paper_agent.schemas.orchestrator import (
    OrchestratorDirective,
    OrchestratorStrategy,
    VenueProfile,
)
from research_paper_agent.schemas.state import ResearchPaperState

logger = logging.getLogger(__name__)


def _extract_json_dict(text: str) -> dict:
    """Extracts a JSON dictionary from raw LLM output even if surrounded by markdown fences or commentary."""
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start:end + 1]

    return json.loads(cleaned)


def master_orchestrator_init_node(state: ResearchPaperState) -> dict:
    """
    Formulates global research strategy, venue guidelines, and word budget allocations
    before downstream agents start.
    """
    node = "master_orchestrator_init"
    
    # Guard: if strategy already exists, keep existing
    if state.get("orchestrator_strategy"):
        return {
            "execution_log": [make_log_entry(node, "SKIP", "Strategy already initialized")],
        }

    topic = state.get("topic", "Autonomous Research Paper")
    paper_type = state.get("paper_type", "technical")
    target_venue = state.get("target_venue", "generic")
    user_prefs = state.get("user_preferences", {})
    compact_mode = state.get("compact_mode", False)

    venue_profile = get_venue_profile(target_venue)

    try:
        prompt_text = build_orchestrator_initial_prompt(
            topic=topic,
            paper_type=paper_type,
            venue_profile=venue_profile,
            user_preferences=user_prefs,
            compact_mode=compact_mode,
        )

        response = llm_strong.invoke([
            SystemMessage(content="You are the Master Orchestrator and Editor-in-Chief. Output strictly valid JSON without markdown fences."),
            HumanMessage(content=prompt_text),
        ])

        raw_text = extract_text_content(response.content)
        parsed = _extract_json_dict(raw_text)

        strategy = OrchestratorStrategy(
            venue_profile=venue_profile,
            strategic_guidance=parsed.get(
                "strategic_guidance",
                f"Develop a high-impact {paper_type} paper on '{topic}' conforming rigorously to {venue_profile.display_name} standards."
            ),
            word_budget_allocation=parsed.get(
                "word_budget_allocation",
                {sec: int(venue_profile.target_word_count / max(len(venue_profile.recommended_sections), 1))
                 for sec in venue_profile.recommended_sections}
            ),
            target_figure_count=int(parsed.get("target_figure_count", venue_profile.figure_count_target)),
            core_focus_areas=parsed.get(
                "core_focus_areas",
                [f"Novel algorithmic approach for {topic}", "Rigorous theoretical formulation", "Comprehensive empirical benchmarking"]
            ),
            compact_mode=compact_mode,
        )

        log_msg = (
            f"Strategy initialized for venue '{venue_profile.venue_key}'. "
            f"Target words: {venue_profile.target_word_count}, Figures: {strategy.target_figure_count}"
        )
        return {
            "orchestrator_strategy": strategy.model_dump(),
            "execution_log": [make_log_entry(node, "SUCCESS", log_msg)],
        }

    except Exception as exc:
        logger.warning(f"Master orchestrator init fallback triggered: {exc}")
        # Robust fallback strategy from venue profile
        default_allocation = {
            sec: int(venue_profile.target_word_count / max(len(venue_profile.recommended_sections), 1))
            for sec in venue_profile.recommended_sections
        }
        fallback_strategy = OrchestratorStrategy(
            venue_profile=venue_profile,
            strategic_guidance=(
                f"Execute a rigorous study on '{topic}' formatted for {venue_profile.display_name}. "
                f"Prioritize clear mathematical formulation, empirical ablation, and reproducible claims."
            ),
            word_budget_allocation=default_allocation,
            target_figure_count=venue_profile.figure_count_target if not compact_mode else 2,
            core_focus_areas=[f"Core foundations of {topic}", "Empirical evaluation", "Theoretical correctness"],
            compact_mode=compact_mode,
        )
        return {
            "orchestrator_strategy": fallback_strategy.model_dump(),
            "errors": [make_error_entry(node, exc, fallback_used="venue_defaults")],
            "execution_log": [make_log_entry(node, "DEGRADED", f"Fallback strategy applied: {exc}")],
        }


def master_orchestrator_review_node(state: ResearchPaperState) -> dict:
    """
    Conducts meta-evaluation of peer review feedback against venue standards.
    Decides whether to proceed to publication or issue targeted section revision directives.
    """
    node = "master_orchestrator_review"
    review_feedback = state.get("review_feedback", [])
    quality_scores = state.get("quality_scores") or {}
    revision_count = state.get("revision_count", 0)
    target_venue = state.get("target_venue", "generic")
    venue_profile = get_venue_profile(target_venue)
    max_revisions = state.get("max_revisions", MAX_REVISION_ITERATIONS)

    # 1. Compute weighted composite score
    weights = ORCHESTRATOR_CONFIG.get("weights", {})
    composite_score = 0.0
    total_weight = 0.0
    for key, weight in weights.items():
        if key in quality_scores:
            composite_score += float(quality_scores[key]) * weight
            total_weight += weight
    
    if total_weight > 0:
        composite_score = composite_score / total_weight
    else:
        composite_score = float(quality_scores.get("overall", QUALITY_GATE_THRESHOLD))

    # Guard: if max revisions reached, enforce proceeding to publication
    if revision_count >= max_revisions:
        directive = OrchestratorDirective(
            action="proceed_to_publication",
            target_sections=[],
            instructions="Maximum revision iterations reached. Proceeding to final compilation.",
            composite_score=round(composite_score, 2),
            component_scores={k: float(v) for k, v in quality_scores.items() if isinstance(v, (int, float))},
            venue_alignment_score=round(composite_score, 2),
            reasoning=f"Paper reached maximum revision limit ({max_revisions}). Final compilation approved.",
        )
        return {
            "orchestrator_directives": [directive.model_dump()],
            "revision_directive": directive.model_dump(),
            "sections_to_revise": [],
            "execution_log": [
                make_log_entry(node, "FINAL_PASS", f"Max revisions reached ({revision_count}/{max_revisions}), score={composite_score:.2f}")
            ],
        }

    # 2. Invoke Gemini for meta-review synthesis
    try:
        prompt_text = build_orchestrator_meta_review_prompt(
            venue_profile=venue_profile,
            review_feedback=review_feedback,
            quality_scores=quality_scores,
            revision_count=revision_count,
            max_revisions=max_revisions,
        )

        response = llm_strong.invoke([
            SystemMessage(content="You are the Senior Area Chair and Master Orchestrator. Return strictly valid JSON without markdown fences."),
            HumanMessage(content=prompt_text),
        ])

        raw_text = extract_text_content(response.content)
        parsed = _extract_json_dict(raw_text)

        action = parsed.get("action", "proceed_to_publication")
        target_sections = parsed.get("target_sections", [])
        instructions = parsed.get("instructions", "")
        reasoning = parsed.get("reasoning", "")
        venue_alignment = float(parsed.get("venue_alignment_score", composite_score))

        # Enforce threshold logic
        if composite_score >= ORCHESTRATOR_CONFIG["min_passing_composite_score"]:
            action = "proceed_to_publication"
            target_sections = []

        directive = OrchestratorDirective(
            action=action,
            target_sections=target_sections,
            instructions=instructions,
            composite_score=round(composite_score, 2),
            component_scores={k: float(v) for k, v in quality_scores.items() if isinstance(v, (int, float))},
            venue_alignment_score=round(venue_alignment, 2),
            reasoning=reasoning,
        )

        new_revision_count = revision_count + (1 if action == "revise_sections" else 0)

        log_status = "PASS" if action == "proceed_to_publication" else "REVISE"
        log_detail = f"action={action}, score={composite_score:.2f}, sections={target_sections}"

        return {
            "orchestrator_directives": [directive.model_dump()],
            "revision_directive": directive.model_dump(),
            "sections_to_revise": target_sections,
            "revision_count": new_revision_count,
            "execution_log": [make_log_entry(node, log_status, log_detail)],
        }

    except Exception as exc:
        logger.warning(f"Master orchestrator review fallback triggered: {exc}")
        # Rule-based fallback decision
        passes = composite_score >= QUALITY_GATE_THRESHOLD
        fallback_action = "proceed_to_publication" if passes else "revise_sections"
        fallback_sections = [] if passes else [1, 2]  # Revise intro / related work or methodology

        directive = OrchestratorDirective(
            action=fallback_action,
            target_sections=fallback_sections,
            instructions="Address critical reviewer comments on technical clarity and citation completeness." if not passes else "",
            composite_score=round(composite_score, 2),
            component_scores={k: float(v) for k, v in quality_scores.items() if isinstance(v, (int, float))},
            venue_alignment_score=round(composite_score, 2),
            reasoning=f"Automated rule-based assessment: score {composite_score:.2f} vs threshold {QUALITY_GATE_THRESHOLD}",
        )

        new_revision_count = revision_count + (1 if fallback_action == "revise_sections" else 0)

        return {
            "orchestrator_directives": [directive.model_dump()],
            "revision_directive": directive.model_dump(),
            "sections_to_revise": fallback_sections,
            "revision_count": new_revision_count,
            "errors": [make_error_entry(node, exc, fallback_used="rule_based_gate")],
            "execution_log": [
                make_log_entry(node, "DEGRADED", f"Rule-based meta-review: action={fallback_action}, score={composite_score:.2f}")
            ],
        }
