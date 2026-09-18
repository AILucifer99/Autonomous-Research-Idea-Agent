"""
Configuration constants for the Research Paper Agent.

All thresholds, retry policies, and model settings are centralised here
so that every node imports from a single source of truth.
"""

from __future__ import annotations

# ── LLM Model Selection ──────────────────────────────────────────────
LLM_MODEL_FAST = "gemini-2.5-flash"
LLM_MODEL_STRONG = "gemini-3.5-flash"
LLM_TEMPERATURE_FAST = 0.2
LLM_TEMPERATURE_STRONG = 0.1

# ── Model & API Pricing (USD) ─────────────────────────────────────────
# Rates per 1M tokens ($) or per call ($)
MODEL_PRICING = {
    "gemini-2.5-flash": {
        "input_cost_per_million": 0.15,
        "output_cost_per_million": 0.60,
    },
    "gemini-3.5-flash": {
        "input_cost_per_million": 1.25,
        "output_cost_per_million": 5.00,
    },
    "gemini-2.5-pro": {
        "input_cost_per_million": 1.25,
        "output_cost_per_million": 5.00,
    },
    "gemini-2.0-flash": {
        "input_cost_per_million": 0.10,
        "output_cost_per_million": 0.40,
    },
    "gemini-1.5-flash": {
        "input_cost_per_million": 0.075,
        "output_cost_per_million": 0.30,
    },
    "gemini-1.5-pro": {
        "input_cost_per_million": 1.25,
        "output_cost_per_million": 5.00,
    },
    "gemini-2.5-flash-image": {
        "cost_per_call": 0.03,
    },
    "tavily_search": {
        "cost_per_call": 0.005,
    },
    "default": {
        "input_cost_per_million": 0.15,
        "output_cost_per_million": 0.60,
    },
}

# ── Quality Gate Thresholds ──────────────────────────────────────────
QUALITY_GATE_THRESHOLD = 7.0       # 0-10, overall score must meet or exceed
NOVELTY_THRESHOLD = 5.0            # 0-10, hypothesis novelty must meet or exceed
MAX_REVISION_ITERATIONS = 2
MAX_RESEARCH_ITERATIONS = 2
MAX_NOVELTY_ITERATIONS = 2

# ── Retry Configuration ─────────────────────────────────────────────
RETRY_LLM = {
    "max_retries": 3,
    "base_delay": 1.0,
    "max_delay": 16.0,
    "jitter": True,
}
RETRY_SEARCH = {
    "max_retries": 2,
    "base_delay": 2.0,
    "max_delay": 8.0,
    "jitter": True,
}
RETRY_IMAGE = {
    "max_retries": 1,
    "base_delay": 2.0,
    "max_delay": 4.0,
    "jitter": False,
}
RETRY_LATEX = {
    "max_retries": 2,
    "base_delay": 3.0,
    "max_delay": 10.0,
    "jitter": False,
}

# ── Paper Defaults ───────────────────────────────────────────────────
PAPER_TYPES = ["technical", "survey", "review", "position", "case_study"]
TARGET_VENUES = [
    "ieee_conference", "ieee_journal", "acm", "springer_lncs",
    "elsevier", "nature", "arxiv", "generic",
]
DEFAULT_SECTIONS = [
    "Abstract", "Introduction", "Related Work", "Methodology",
    "Mathematical Formulation", "Experiment Design", "Results",
    "Discussion", "Limitations", "Future Work", "Conclusion",
]

# ── Search Defaults ──────────────────────────────────────────────────
MAX_SEARCH_QUERIES = 12
MAX_RESULTS_PER_QUERY = 6
MIN_VALIDATED_SOURCES = 3

# ── Section Word Ranges ─────────────────────────────────────────────
SECTION_WORD_RANGES = {
    "abstract": (150, 300),
    "introduction": (500, 1200),
    "related_work": (600, 1500),
    "methodology": (500, 1500),
    "math_formulation": (400, 1000),
    "experiment": (400, 1000),
    "results": (400, 1200),
    "discussion": (400, 1000),
    "limitations": (200, 500),
    "future_work": (200, 500),
    "conclusion": (200, 500),
    "appendix": (200, 800),
}

# ── Orchestrator & HITL Pre-Flight Safeguards ───────────────────────
MAX_UNCONFIRMED_API_CALLS = 18       # Trigger interactive approval if estimated calls > 18
MAX_ESTIMATED_COST_THRESHOLD = 0.50  # Trigger interactive approval if estimated cost > $0.50 (USD)

ORCHESTRATOR_CONFIG = {
    "enabled": True,
    "model": LLM_MODEL_STRONG,        # Gemini 3.5 Flash for high-level reasoning & planning
    "decision_temperature": 0.1,
    "max_allowed_revisions": MAX_REVISION_ITERATIONS,
    "compact_mode_reduction_ratio": 0.6,  # Scales down queries, figures, and sections in compact mode
    "min_passing_composite_score": 7.5,
    "weights": {
        "technical_depth": 0.30,
        "academic_coherence": 0.25,
        "citation_integrity": 0.20,
        "novelty": 0.15,
        "structure_and_format": 0.10,
    },
}
