"""
LaTeX-specific schemas: template config, compilation results.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

__all__ = [
    "LaTeXConfig",
    "LaTeXCompilationResult",
    "GeneratedFigure",
]


class LaTeXConfig(BaseModel):
    template: Literal[
        "ieee_conference", "ieee_journal", "acm", "springer_lncs",
        "elsevier", "nature", "arxiv", "generic",
    ] = "arxiv"
    bibliography_style: str = "IEEEtran"
    extra_packages: List[str] = Field(default_factory=list)


class LaTeXCompilationResult(BaseModel):
    success: bool = False
    pdf_path: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class GeneratedFigure(BaseModel):
    figure_id: int
    filename: str
    path: str = ""
    caption: str = ""
    label: str = ""
    generation_method: str = "gemini_image"
    success: bool = True
    error: Optional[str] = None
