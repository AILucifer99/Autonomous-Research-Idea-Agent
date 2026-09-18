"""
Design-phase schemas: methodology, mathematical artifacts, experiment, data analysis, figures.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

__all__ = [
    "Methodology",
    "MathArtifact",
    "MathModelingResult",
    "ExperimentDesign",
    "AnalysisResults",
    "FigureSpec",
    "FigurePlan",
]


class Methodology(BaseModel):
    approach: str
    steps: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    innovation_points: List[str] = Field(default_factory=list)
    required_data: List[str] = Field(default_factory=list)
    evaluation_strategy: str = ""


class MathArtifact(BaseModel):
    id: int
    name: str
    environment: Literal[
        "equation", "align", "gather", "split", "cases",
        "matrix", "bmatrix", "pmatrix",
        "theorem", "lemma", "corollary", "proof",
        "definition", "proposition",
        "algorithm", "algorithmic",
    ] = "equation"
    latex_source: str
    variable_definitions: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    derivation_notes: str = ""
    validation_notes: str = ""


class MathModelingResult(BaseModel):
    artifacts: List[MathArtifact] = Field(default_factory=list)
    preamble_packages: List[str] = Field(
        default_factory=lambda: [
            "amsmath", "amssymb", "amsthm", "algorithm", "algorithmic",
        ]
    )


class ExperimentDesign(BaseModel):
    objective: str
    datasets: List[str] = Field(default_factory=list)
    baselines: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    evaluation_protocol: str = ""
    hyperparameters: List[str] = Field(default_factory=list)
    reproducibility_notes: str = ""


class AnalysisResults(BaseModel):
    analysis_framework: str = ""
    statistical_tests: List[str] = Field(default_factory=list)
    expected_outcomes: List[str] = Field(default_factory=list)
    interpretation_guidelines: str = ""
    ablation_studies: List[str] = Field(default_factory=list)


class FigureSpec(BaseModel):
    id: int
    figure_type: Literal[
        "architecture", "workflow", "chart", "table",
        "plot", "diagram", "conceptual", "comparison",
    ] = "diagram"
    caption: str
    label: str = Field(description="LaTeX label, e.g. fig:architecture")
    description: str = ""
    generation_method: Literal["gemini_image", "tikz", "pgfplots", "table_latex"] = "gemini_image"
    prompt: Optional[str] = None
    tikz_code: Optional[str] = None
    placement: Literal["t", "b", "h", "H", "p"] = "t"


class FigurePlan(BaseModel):
    figures: List[FigureSpec] = Field(default_factory=list)
