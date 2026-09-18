"""Data Analyst — Node 14."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_fast
from research_paper_agent.schemas.design import AnalysisResults
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.design_prompts import DATA_ANALYST_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def data_analyst_node(state: ResearchPaperState) -> dict:
    node = "data_analyst"
    try:
        analyst = llm_fast.with_structured_output(AnalysisResults)
        result = analyst.invoke([
            SystemMessage(content=DATA_ANALYST_SYSTEM),
            HumanMessage(content=(
                f"Experiment design:\n{state.get('experiment_design', {})}\n\n"
                f"Methodology:\n{state.get('methodology', {})}"
            )),
        ])
        return {"analysis_results": result.model_dump(),
                "execution_log": [make_log_entry(node, "SUCCESS", "analysis_framework_designed")]}
    except Exception as exc:
        return {"analysis_results": {"analysis_framework": "", "statistical_tests": [],
                "expected_outcomes": [], "interpretation_guidelines": "", "ablation_studies": []},
                "errors": [make_error_entry(node, exc, fallback_used="empty_analysis")],
                "execution_log": [make_log_entry(node, "DEGRADED", str(exc))]}
