"""
Review Agents — Nodes 21-25 + Quality Assessor.
All review nodes in one file since they follow the same pattern.
"""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_strong, llm_fast
from research_paper_agent.schemas.review import ReviewFeedback, QualityScores
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.review_prompts import (
    SCIENTIFIC_REVIEWER_SYSTEM, FACT_VERIFIER_SYSTEM,
    CONSISTENCY_VALIDATOR_SYSTEM, STATISTICAL_REVIEWER_SYSTEM,
    REPRODUCIBILITY_REVIEWER_SYSTEM, QUALITY_ASSESSOR_SYSTEM,
)
from research_paper_agent.errors import make_error_entry, make_log_entry


def _review_node(state: ResearchPaperState, reviewer_type: str,
                 system_prompt: str, llm, context_builder) -> dict:
    """Generic review node factory."""
    node = f"{reviewer_type}_reviewer"
    try:
        reviewer = llm.with_structured_output(ReviewFeedback)
        context = context_builder(state)
        feedback = reviewer.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=context),
        ])
        # Force the correct reviewer_type
        fb = feedback.model_dump()
        fb["reviewer_type"] = reviewer_type
        return {
            "review_feedback": [fb],
            "execution_log": [make_log_entry(node, "SUCCESS",
                              f"score={feedback.score} issues={len(feedback.issues)}")],
        }
    except Exception as exc:
        return {
            "review_feedback": [{"reviewer_type": reviewer_type, "score": 5.0,
                                 "issues": [], "strengths": [], "revision_instructions": ""}],
            "errors": [make_error_entry(node, exc, fallback_used="default_score")],
            "execution_log": [make_log_entry(node, "DEGRADED", str(exc))],
        }


def scientific_reviewer_node(state: ResearchPaperState) -> dict:
    return _review_node(state, "scientific", SCIENTIFIC_REVIEWER_SYSTEM, llm_strong,
                        lambda s: (
                            f"Paper body:\n{s.get('merged_paper_tex', '')[:6000]}\n\n"
                            f"Hypothesis:\n{s.get('selected_hypothesis', {})}\n\n"
                            f"Methodology:\n{s.get('methodology', {})}"
                        ))


def fact_verifier_node(state: ResearchPaperState) -> dict:
    return _review_node(state, "factual", FACT_VERIFIER_SYSTEM, llm_strong,
                        lambda s: (
                            f"Paper body:\n{s.get('merged_paper_tex', '')[:6000]}\n\n"
                            f"Evidence chunks:\n{s.get('evidence_chunks', [])[:15]}\n\n"
                            f"Validated sources:\n{s.get('validated_sources', [])[:10]}"
                        ))


def consistency_validator_node(state: ResearchPaperState) -> dict:
    return _review_node(state, "consistency", CONSISTENCY_VALIDATOR_SYSTEM, llm_fast,
                        lambda s: (
                            f"Paper body:\n{s.get('merged_paper_tex', '')[:6000]}\n\n"
                            f"Paper outline:\n{s.get('paper_outline', {})}"
                        ))


def statistical_reviewer_node(state: ResearchPaperState) -> dict:
    return _review_node(state, "statistical", STATISTICAL_REVIEWER_SYSTEM, llm_strong,
                        lambda s: (
                            f"Paper body:\n{s.get('merged_paper_tex', '')[:6000]}\n\n"
                            f"Math artifacts:\n{s.get('math_artifacts', [])}\n\n"
                            f"Experiment design:\n{s.get('experiment_design', {})}"
                        ))


def reproducibility_reviewer_node(state: ResearchPaperState) -> dict:
    return _review_node(state, "reproducibility", REPRODUCIBILITY_REVIEWER_SYSTEM, llm_fast,
                        lambda s: (
                            f"Paper body:\n{s.get('merged_paper_tex', '')[:6000]}\n\n"
                            f"Methodology:\n{s.get('methodology', {})}\n\n"
                            f"Experiment design:\n{s.get('experiment_design', {})}"
                        ))


def quality_assessor_node(state: ResearchPaperState) -> dict:
    """Aggregate all review feedback into composite quality scores."""
    node = "quality_assessor"
    feedback = state.get("review_feedback", [])
    try:
        assessor = llm_strong.with_structured_output(QualityScores)
        scores = assessor.invoke([
            SystemMessage(content=QUALITY_ASSESSOR_SYSTEM),
            HumanMessage(content=f"Review feedback:\n{feedback}"),
        ])
        return {
            "quality_scores": scores.model_dump(),
            "execution_log": [make_log_entry(node, "SUCCESS",
                              f"overall={scores.overall} passes={scores.passes_gate}")],
        }
    except Exception as exc:
        return {
            "quality_scores": {"technical_accuracy": 5.0, "novelty": 5.0,
                               "methodology_quality": 5.0, "mathematical_rigor": 5.0,
                               "citation_quality": 5.0, "coherence": 5.0,
                               "reproducibility": 5.0, "publication_readiness": 5.0,
                               "overall": 5.0, "passes_gate": False, "summary": ""},
            "errors": [make_error_entry(node, exc, fallback_used="default_scores")],
            "execution_log": [make_log_entry(node, "DEGRADED", str(exc))],
        }
