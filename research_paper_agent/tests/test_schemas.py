# Schema test assertions without pytest dependency

from research_paper_agent.schemas.research import SearchQuery, ResearchPlan, LiteratureResult, ValidatedSource, EvidenceChunk
from research_paper_agent.schemas.knowledge import ResearchGap, KnowledgeGraph
from research_paper_agent.schemas.innovation import Hypothesis, NoveltyAssessment
from research_paper_agent.schemas.design import MathArtifact, FigureSpec, ExperimentDesign, Methodology
from research_paper_agent.schemas.drafting import SectionTask, PaperOutline
from research_paper_agent.schemas.review import QualityScores, ReviewFeedback, ReviewIssue


def test_search_query_schema():
    q = SearchQuery(id=1, query_text="State space models vs transformers", priority="high")
    assert q.id == 1
    assert q.priority == "high"


def test_research_plan_schema():
    plan = ResearchPlan(
        title_working="Hybrid State Space Models",
        field="Artificial Intelligence",
        sub_field="Natural Language Processing",
        research_question="Can Mamba hybrids exceed standard attention in long-context reasoning?",
        depth_level="deep",
        queries=[SearchQuery(id=1, query_text="Mamba Transformer hybrid architectures")],
        expected_sections=["Introduction", "Methodology", "Experiments"],
    )
    assert len(plan.queries) == 1
    assert plan.depth_level == "deep"


def test_math_artifact_schema():
    ma = MathArtifact(
        id=1,
        name="State Recurrence Equation",
        environment="equation",
        latex_source=r"h_t = \mathbf{A} h_{t-1} + \mathbf{B} x_t",
        variable_definitions=["h_t: hidden state", "x_t: input vector"],
        assumptions=["Discrete linear time-invariant system"],
    )
    assert ma.environment == "equation"
    assert "h_t" in ma.latex_source


def test_figure_spec_schema():
    fig = FigureSpec(
        id=1,
        figure_type="architecture",
        caption="Hybrid Block Architecture Overview",
        label="fig:arch",
        description="Block diagram comparing attention and recurrent gating",
        generation_method="gemini_image",
    )
    assert fig.figure_type == "architecture"
    assert fig.placement == "t"


def test_quality_scores_schema():
    qs = QualityScores(
        technical_accuracy=8.5,
        novelty=7.5,
        methodology_quality=8.0,
        mathematical_rigor=8.0,
        citation_quality=9.0,
        coherence=8.5,
        reproducibility=7.0,
        publication_readiness=8.0,
        overall=8.1,
        passes_gate=True,
    )
    assert qs.overall >= 7.0
    assert qs.passes_gate is True
