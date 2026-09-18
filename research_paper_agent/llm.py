"""
Gemini LLM instances for the Research Paper Agent.

Follows the pattern from notebook 5_bwa_image.ipynb (L135-138):
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)

Two tiers:
    llm_fast   — planning, extraction, drafting, simple review
    llm_strong — deep reasoning, math, critical review, novelty
"""

from __future__ import annotations

from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from research_paper_agent.config import (
    LLM_MODEL_FAST,
    LLM_MODEL_STRONG,
    LLM_TEMPERATURE_FAST,
    LLM_TEMPERATURE_STRONG,
)
from research_paper_agent.cost_tracker import default_cost_callback

load_dotenv()

# ── Fast model (gemini-2.5-flash) ────────────────────────────────────
llm_fast = ChatGoogleGenerativeAI(
    model=LLM_MODEL_FAST,
    temperature=LLM_TEMPERATURE_FAST,
    callbacks=[default_cost_callback],
)

# ── Strong model (gemini-2.5-pro / gemini-3.5-flash) ───────────────────
llm_strong = ChatGoogleGenerativeAI(
    model=LLM_MODEL_STRONG,
    temperature=LLM_TEMPERATURE_STRONG,
    callbacks=[default_cost_callback],
)


def extract_text_content(content: Any) -> str:
    """Safely extracts a plain string from str, list of parts, or structured response content."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", str(item)))
            elif hasattr(item, "text"):
                parts.append(getattr(item, "text", ""))
            else:
                parts.append(str(item))
        return "".join(parts).strip()
    return str(content).strip()
