"""
Drafting-phase schemas: paper outline, section tasks, citation management.

Follows the existing Task / Plan pattern (bwa_backend.py L31-50).
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

__all__ = [
    "SectionTask",
    "PaperOutline",
    "BibEntry",
    "CitationPlan",
    "CitationReport",
]


class SectionTask(BaseModel):
    id: int
    title: str
    section_type: Literal[
        "abstract", "introduction", "related_work", "methodology",
        "math_formulation", "experiment", "results", "discussion",
        "limitations", "future_work", "conclusion", "appendix",
    ] = "introduction"
    goal: str = Field(..., description="One sentence describing the purpose of this section.")
    key_points: List[str] = Field(..., min_length=3, max_length=8)
    target_words: int = Field(..., ge=150, le=2000)
    assigned_evidence_ids: List[int] = Field(default_factory=list)
    assigned_math_ids: List[int] = Field(default_factory=list)
    assigned_figure_ids: List[int] = Field(default_factory=list)
    requires_citations: bool = True
    requires_methodology: bool = False
    requires_math: bool = False


class PaperOutline(BaseModel):
    paper_title: str
    abstract_plan: str = ""
    sections: List[SectionTask]
    bibliography_strategy: Literal["ieee", "acm", "springer", "apa", "nature", "elsevier"] = "ieee"


class BibEntry(BaseModel):
    key: str = Field(description="BibTeX citation key, e.g. vaswani2017attention")
    entry_type: Literal["article", "inproceedings", "book", "misc", "techreport", "phdthesis"] = "article"
    title: str
    authors: str = ""
    year: str = ""
    journal: Optional[str] = None
    booktitle: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None

    def to_bibtex(self) -> str:
        """Render this entry as a BibTeX string."""
        lines = [f"@{self.entry_type}{{{self.key},"]
        for field_name in ["title", "authors", "year", "journal", "booktitle",
                           "volume", "pages", "publisher", "url", "doi"]:
            val = getattr(self, field_name, None)
            if val:
                bib_field = "author" if field_name == "authors" else field_name
                lines.append(f"  {bib_field} = {{{val}}},")
        lines.append("}")
        return "\n".join(lines)


class CitationPlan(BaseModel):
    bib_entries: List[BibEntry] = Field(default_factory=list)
    tex_with_citations: str = ""


class CitationReport(BaseModel):
    total_citations: int = 0
    unique_sources: int = 0
    orphan_citations: List[str] = Field(default_factory=list)
    missing_bib_entries: List[str] = Field(default_factory=list)
    duplicate_keys: List[str] = Field(default_factory=list)
    is_valid: bool = True
