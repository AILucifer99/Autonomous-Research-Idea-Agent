"""
Orchestrator Guide: The central knowledge base, venue standards matrix,
pre-flight resource estimator, and prompt enhancement engine for the Master Orchestrator.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from research_paper_agent.config import (
    MAX_ESTIMATED_COST_THRESHOLD,
    MAX_REVISION_ITERATIONS,
    MAX_UNCONFIRMED_API_CALLS,
    MODEL_PRICING,
    ORCHESTRATOR_CONFIG,
    SECTION_WORD_RANGES,
)
from research_paper_agent.schemas.orchestrator import (
    OrchestratorDirective,
    PreFlightEstimate,
    VenueProfile,
)

logger = logging.getLogger(__name__)

# ── Venue Standards Knowledge Matrix ─────────────────────────────────
VENUE_STANDARDS: Dict[str, VenueProfile] = {
    "ieee_conference": VenueProfile(
        venue_key="ieee_conference",
        display_name="IEEE Conference Proceedings (e.g. CVPR, ICCV, ICRA, INFOCOM)",
        target_word_count=5500,
        max_pages=8,
        recommended_sections=[
            "Abstract", "Introduction", "Related Work", "System Architecture & Methodology",
            "Theoretical Formulation", "Performance Evaluation", "Ablation Studies", "Conclusion",
        ],
        tone="concise, mathematically rigorous, engineering-focused, authoritative",
        math_depth="rigorous",
        citation_style="IEEE numeric [1], [2]",
        figure_count_target=5,
        key_rubrics=[
            "Clear technical contribution over state-of-the-art baselines",
            "Rigorous empirical benchmark metrics and ablation studies",
            "Reproducible mathematical formulation and pseudo-code",
            "Adherence to IEEE two-column typographic expectations",
        ],
    ),
    "ieee_journal": VenueProfile(
        venue_key="ieee_journal",
        display_name="IEEE Transactions / Journal",
        target_word_count=9000,
        max_pages=14,
        recommended_sections=[
            "Abstract", "Introduction", "Related Work & Background", "Problem Formulation",
            "Proposed Framework & Algorithms", "Theoretical Analysis & Proofs",
            "Experimental Setup", "Results & Comparative Analysis", "Discussion & Limitations", "Conclusion",
        ],
        tone="exhaustive, mathematically sound, deeply analytical, authoritative",
        math_depth="rigorous",
        citation_style="IEEE numeric [1], [2]",
        figure_count_target=6,
        key_rubrics=[
            "Comprehensive theoretical grounding and formal correctness proofs",
            "Extensive empirical comparisons across multiple benchmark suites",
            "In-depth analysis of computational complexity and edge cases",
        ],
    ),
    "acm": VenueProfile(
        venue_key="acm",
        display_name="ACM Conference / Journal (e.g. SIGKDD, SIGMOD, CHI, CCS)",
        target_word_count=6500,
        max_pages=10,
        recommended_sections=[
            "Abstract", "Introduction", "Background & Motivation", "System Design & Methodology",
            "Algorithmic Modeling", "Empirical Evaluation", "Related Work", "Discussion", "Conclusion",
        ],
        tone="principled, architecture-centric, academically rigorous",
        math_depth="rigorous",
        citation_style="ACM author-year / numeric bracket",
        figure_count_target=5,
        key_rubrics=[
            "Clear systems or algorithmic novelty",
            "Thorough methodology and reproducibility discussion",
            "Robust empirical methodology with statistical significance tests",
        ],
    ),
    "nature": VenueProfile(
        venue_key="nature",
        display_name="Nature / Science High-Impact Journal",
        target_word_count=4500,
        max_pages=6,
        recommended_sections=[
            "Abstract", "Introduction", "Main Findings", "Mechanistic & Theoretical Insights",
            "Broader Implications", "Methods",
        ],
        tone="accessible to multidisciplinary scientists, punchy, paradigm-shifting, narrative-driven",
        math_depth="applied",
        citation_style="Superscript numeric",
        figure_count_target=4,
        key_rubrics=[
            "High multidisciplinary interest and paradigm-shifting significance",
            "Clear visual narrative and conceptual diagrams",
            "Explicit statement of mechanism and real-world implications",
        ],
    ),
    "arxiv": VenueProfile(
        venue_key="arxiv",
        display_name="arXiv Preprint (Open Science)",
        target_word_count=7000,
        max_pages=None,
        recommended_sections=[
            "Abstract", "Introduction", "Related Work", "Methodology",
            "Theoretical Guarantees", "Experiments & Findings", "Discussion",
            "Limitations & Ethical Considerations", "Conclusion", "Appendix",
        ],
        tone="comprehensive, transparent, reproducible, academic",
        math_depth="rigorous",
        citation_style="Numeric or Author-Year",
        figure_count_target=5,
        key_rubrics=[
            "Complete clarity of implementation details and hyperparameters",
            "Honest treatment of failure modes and computational boundaries",
            "Exhaustive literature context and clear attribution",
        ],
    ),
    "springer_lncs": VenueProfile(
        venue_key="springer_lncs",
        display_name="Springer LNCS (e.g. ECCV, MICCAI, ESWC)",
        target_word_count=5800,
        max_pages=14,
        recommended_sections=[
            "Abstract", "Introduction", "Related Work", "Method",
            "Experiments", "Results and Analysis", "Conclusion",
        ],
        tone="concise, structured, academic",
        math_depth="rigorous",
        citation_style="LNCS numeric [1]",
        figure_count_target=4,
        key_rubrics=[
            "Strict adherence to single-column LNCS layout constraints",
            "Clear benchmark rankings and error metrics",
        ],
    ),
    "elsevier": VenueProfile(
        venue_key="elsevier",
        display_name="Elsevier Peer-Reviewed Journal",
        target_word_count=7500,
        max_pages=12,
        recommended_sections=[
            "Abstract", "Introduction", "Literature Review", "Proposed Methodology",
            "Experimental Verification", "Results and Discussion", "Conclusion",
        ],
        tone="methodical, thorough, formal",
        math_depth="rigorous",
        citation_style="Elsevier Harvard or Numeric",
        figure_count_target=5,
        key_rubrics=[
            "Deep literature review demonstrating research gap",
            "Detailed experimental verification and sensitivity analysis",
        ],
    ),
    "generic": VenueProfile(
        venue_key="generic",
        display_name="General Academic Peer-Reviewed Paper",
        target_word_count=6000,
        max_pages=10,
        recommended_sections=[
            "Abstract", "Introduction", "Related Work", "Methodology",
            "Mathematical Formulation", "Experiment Design", "Results",
            "Discussion", "Limitations", "Conclusion",
        ],
        tone="scholarly, objective, well-substantiated",
        math_depth="rigorous",
        citation_style="Numeric [1]",
        figure_count_target=4,
        key_rubrics=[
            "Coherent narrative from hypothesis to experimental validation",
            "Balanced technical depth across all sections",
            "Accurate citations and verifiable claims",
        ],
    ),
}


def get_venue_profile(venue_key: str) -> VenueProfile:
    """Retrieve or derive the VenueProfile for a specified venue key."""
    normalized = (venue_key or "generic").strip().lower().replace(" ", "_").replace("-", "_")
    if normalized in VENUE_STANDARDS:
        return VENUE_STANDARDS[normalized]
    
    # Partial match fallback
    for key, profile in VENUE_STANDARDS.items():
        if key in normalized or normalized in key:
            return profile
            
    # Default fallback
    base = VENUE_STANDARDS["generic"]
    return base.model_copy(update={"venue_key": normalized, "display_name": venue_key.title()})


def compute_preflight_estimate(
    topic: str,
    paper_type: str = "technical",
    target_venue: str = "ieee_conference",
    user_preferences: Optional[Dict[str, Any]] = None,
    compact_mode: bool = False,
) -> PreFlightEstimate:
    """
    Computes upfront resource, token, cost, and API call estimates.
    
    Flags `requires_human_confirmation` if:
      - Total estimated external calls > MAX_UNCONFIRMED_API_CALLS (18)
      - Estimated USD cost > MAX_ESTIMATED_COST_THRESHOLD ($0.50)
      - Or explicit safety/budget constraints are set
    """
    prefs = user_preferences or {}
    venue = get_venue_profile(target_venue)

    # 1. Estimate sections to draft
    num_sections = len(venue.recommended_sections)
    if compact_mode:
        num_sections = min(num_sections, 6)
        
    # 2. Estimate LLM calls
    # Breakdown:
    # - Master orchestrator init (1)
    # - Research planner (1)
    # - Domain analysis & Gap analysis (1)
    # - Hypothesis generator & Novelty evaluator (2)
    # - Methodology & Math & Experiment & Data analysis & Figure planner & Outline (6)
    # - Section drafting (num_sections calls)
    # - Citation manager / BibTeX synthesis (1)
    # - Review subgraph: 5 reviewers + 1 quality assessor (6 calls)
    # - Master orchestrator review meta-evaluation (1)
    # - Export & traceability (1)
    # Plus potential revision loops (default estimate assumes 0 revisions on first pass)
    base_llm_calls = 1 + 1 + 1 + 2 + 6 + num_sections + 1 + 6 + 1 + 1
    
    # 3. Estimate search queries
    if compact_mode:
        search_queries = 4
    elif paper_type in ("survey", "review"):
        search_queries = 10
    else:
        search_queries = 6

    # 4. Estimate image generation calls
    if compact_mode:
        image_calls = 2
    else:
        image_calls = min(venue.figure_count_target, 5)

    total_api_calls = base_llm_calls + search_queries + image_calls

    # 5. Estimate tokens
    # Gemini Flash models:
    # Average prompt tokens per call ~ 1,800 tokens; output tokens ~ 1,200 tokens
    # Section drafting has larger outputs (~ 1,500 words = ~2,000 tokens)
    avg_input_tokens_per_call = 2200
    avg_output_tokens_per_call = 1100
    if compact_mode:
        avg_input_tokens_per_call = 1400
        avg_output_tokens_per_call = 700

    estimated_input_tokens = base_llm_calls * avg_input_tokens_per_call
    estimated_output_tokens = base_llm_calls * avg_output_tokens_per_call
    estimated_total_tokens = estimated_input_tokens + estimated_output_tokens

    # 6. Estimate costs
    strong_model_price = MODEL_PRICING.get("gemini-3.5-flash", MODEL_PRICING["default"])
    fast_model_price = MODEL_PRICING.get("gemini-2.5-flash", MODEL_PRICING["default"])
    image_price = MODEL_PRICING.get("gemini-2.5-flash-image", {}).get("cost_per_call", 0.03)
    search_price = MODEL_PRICING.get("tavily_search", {}).get("cost_per_call", 0.005)

    # Assume 30% calls use strong model (planning, orchestrator, review assessor)
    # and 70% calls use fast model (drafting, parallel reviewers, analysis)
    strong_calls = int(base_llm_calls * 0.3)
    fast_calls = base_llm_calls - strong_calls

    llm_cost = (
        (strong_calls * avg_input_tokens_per_call / 1_000_000 * strong_model_price["input_cost_per_million"])
        + (strong_calls * avg_output_tokens_per_call / 1_000_000 * strong_model_price["output_cost_per_million"])
        + (fast_calls * avg_input_tokens_per_call / 1_000_000 * fast_model_price["input_cost_per_million"])
        + (fast_calls * avg_output_tokens_per_call / 1_000_000 * fast_model_price["output_cost_per_million"])
    )
    search_cost = search_queries * search_price
    image_cost = image_calls * image_price
    total_cost_usd = round(llm_cost + search_cost + image_cost, 4)

    # 7. Check HITL thresholds
    reasons: List[str] = []
    if total_api_calls > MAX_UNCONFIRMED_API_CALLS:
        reasons.append(
            f"Estimated total API calls ({total_api_calls}) exceeds safety threshold ({MAX_UNCONFIRMED_API_CALLS})"
        )
    if total_cost_usd > MAX_ESTIMATED_COST_THRESHOLD:
        reasons.append(
            f"Estimated total cost (${total_cost_usd:.3f}) exceeds threshold (${MAX_ESTIMATED_COST_THRESHOLD:.2f})"
        )
    if prefs.get("always_confirm", False):
        reasons.append("User requested interactive confirmation before execution")

    requires_confirmation = len(reasons) > 0

    # Latency estimation: ~60s parallel base + 5s per section + image generation
    estimated_duration = 45 + (num_sections * 4) + (image_calls * 5)
    if compact_mode:
        estimated_duration = int(estimated_duration * 0.65)

    return PreFlightEstimate(
        estimated_llm_calls=base_llm_calls,
        estimated_search_queries=search_queries,
        estimated_image_calls=image_calls,
        estimated_total_tokens=estimated_total_tokens,
        estimated_cost_usd=total_cost_usd,
        requires_human_confirmation=requires_confirmation,
        reasons_for_confirmation=reasons,
        compact_mode_available=True,
        estimated_duration_seconds=estimated_duration,
    )


# ── Prompt Generation Helpers ─────────────────────────────────────────

def build_orchestrator_initial_prompt(
    topic: str,
    paper_type: str,
    venue_profile: VenueProfile,
    user_preferences: Dict[str, Any],
    compact_mode: bool = False,
) -> str:
    """Builds the system/user instruction prompt for Master Orchestrator initialization."""
    rubrics_formatted = "\n".join(f"- {r}" for r in venue_profile.key_rubrics)
    sections_formatted = ", ".join(venue_profile.recommended_sections)
    
    mode_instructions = ""
    if compact_mode:
        mode_instructions = (
            "\n**COMPACT MODE ACTIVE**: Optimize strictly for speed and concise high-density clarity. "
            "Reduce peripheral sections, keep word count at approximately 60% of standard target, "
            "and limit visual artifacts to 2 high-impact figures."
        )

    return f"""You are the Master Orchestrator Agent for an autonomous academic research paper laboratory.
You are powered by Gemini and function as the principal investigator and editor-in-chief overseeing
a team of specialised sub-agents (Literature Discovery, Methodologist, Math Modeler, Section Drafters, Reviewers).

### RESEARCH ASSIGNMENT:
- **Research Topic**: {topic}
- **Paper Type**: {paper_type}
- **Target Venue**: {venue_profile.display_name} ({venue_profile.venue_key})
- **Target Word Count**: {venue_profile.target_word_count} words
- **Tone & Style**: {venue_profile.tone}
- **Mathematical Depth**: {venue_profile.math_depth}
- **Citation Style**: {venue_profile.citation_style}
- **Target Figures**: {venue_profile.figure_count_target}{mode_instructions}

### VENUE REVIEW CRITERIA & RUBRICS:
{rubrics_formatted}

### RECOMMENDED OUTLINE SECTIONS:
{sections_formatted}

### USER PREFERENCES & CONSTRAINTS:
{user_preferences}

### YOUR MANDATE:
Formulate an overarching strategy that guides the specialized sub-agents. You must produce a JSON object with:
1. `strategic_guidance`: 3-5 sentences of authoritative instructions detailing the core angle, thesis, methodological priorities, and theoretical rigor required.
2. `core_focus_areas`: 3-5 priority themes or novel mechanisms the paper must center on.
3. `word_budget_allocation`: A dictionary mapping section names to their recommended word targets matching the total {venue_profile.target_word_count} words.
4. `target_figure_count`: Integer target for illustrative figures.

Return ONLY a valid JSON object matching these keys.
"""


def build_orchestrator_meta_review_prompt(
    venue_profile: VenueProfile,
    review_feedback: List[Dict[str, Any]],
    quality_scores: Dict[str, Any],
    revision_count: int,
    max_revisions: int = MAX_REVISION_ITERATIONS,
) -> str:
    """Builds the prompt for the Master Orchestrator to meta-evaluate peer reviews."""
    rubrics_formatted = "\n".join(f"- {r}" for r in venue_profile.key_rubrics)
    reviews_text = ""
    for idx, rev in enumerate(review_feedback, 1):
        reviewer = rev.get("reviewer", f"Reviewer #{idx}")
        score = rev.get("score", "N/A")
        comments = rev.get("critique", rev.get("comments", str(rev)))[:400]
        reviews_text += f"\n[{reviewer}] (Score: {score}/10):\n{comments}\n"

    return f"""You are the Master Orchestrator and Senior Area Chair for {venue_profile.display_name}.
You are conducting a meta-review and quality arbitration on the compiled paper.

### VENUE QUALITY STANDARDS:
{rubrics_formatted}
- Minimum Passing Composite Score: {ORCHESTRATOR_CONFIG['min_passing_composite_score']}/10
- Current Revision Count: {revision_count} (Maximum allowed: {max_revisions})

### AUTOMATED QUALITY SCORES:
{quality_scores}

### REVIEWER FEEDBACK:
{reviews_text}

### YOUR META-DECISION:
Determine whether the manuscript meets publication quality for {venue_profile.display_name}.
If the score is adequate (>= {ORCHESTRATOR_CONFIG['min_passing_composite_score']}) OR revision limit ({max_revisions}) is reached:
  - action: "proceed_to_publication"
If critical deficiencies exist and revision limit is not reached:
  - action: "revise_sections"
  - target_sections: list of 1-based integer indices of sections requiring rewriting
  - instructions: specific, actionable rewrite directives addressing reviewer critiques.

Output ONLY a valid JSON object with:
- "action": "proceed_to_publication" or "revise_sections"
- "composite_score": float between 0.0 and 10.0
- "venue_alignment_score": float between 0.0 and 10.0
- "target_sections": list of integers (empty if proceeding)
- "instructions": string guidance for authors/drafters
- "reasoning": 2-3 sentences explaining your meta-verdict.
"""
