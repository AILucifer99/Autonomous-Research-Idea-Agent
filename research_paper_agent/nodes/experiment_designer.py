"""Experiment Designer — Node 13."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_fast
from research_paper_agent.schemas.design import ExperimentDesign
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.design_prompts import EXPERIMENT_DESIGNER_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def experiment_designer_node(state: ResearchPaperState) -> dict:
    node = "experiment_designer"
    try:
        designer = llm_fast.with_structured_output(ExperimentDesign)
        result = designer.invoke([
            SystemMessage(content=EXPERIMENT_DESIGNER_SYSTEM),
            HumanMessage(content=(
                f"Methodology:\n{state.get('methodology', {})}\n\n"
                f"Math artifacts:\n{state.get('math_artifacts', [])}\n\n"
                f"Selected hypothesis:\n{state.get('selected_hypothesis', {})}"
            )),
        ])
        return {"experiment_design": result.model_dump(),
                "execution_log": [make_log_entry(node, "SUCCESS",
                                  f"baselines={len(result.baselines)} metrics={len(result.metrics)}")]}
    except Exception as exc:
        return {"experiment_design": {"objective": "", "datasets": [], "baselines": [],
                "metrics": [], "evaluation_protocol": "", "hyperparameters": [], "reproducibility_notes": ""},
                "errors": [make_error_entry(node, exc, fallback_used="empty_experiment")],
                "execution_log": [make_log_entry(node, "DEGRADED", str(exc))]}
