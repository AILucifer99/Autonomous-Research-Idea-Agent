"""
Review Subgraph — 6-stage review and quality assessment pipeline.

Follows the existing reducer subgraph pattern from bwa_backend.py L527-536:
    reducer_graph = StateGraph(State)
    ...
    reducer_subgraph = reducer_graph.compile()
"""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.nodes import (
    scientific_reviewer_node,
    fact_verifier_node,
    consistency_validator_node,
    statistical_reviewer_node,
    reproducibility_reviewer_node,
    quality_assessor_node,
)

review_graph = StateGraph(ResearchPaperState)

review_graph.add_node("scientific_reviewer", scientific_reviewer_node)
review_graph.add_node("fact_verifier", fact_verifier_node)
review_graph.add_node("consistency_validator", consistency_validator_node)
review_graph.add_node("statistical_reviewer", statistical_reviewer_node)
review_graph.add_node("reproducibility_reviewer", reproducibility_reviewer_node)
review_graph.add_node("quality_assessor", quality_assessor_node)

# Parallel fan-out from START to all independent reviewers
review_graph.add_edge(START, "scientific_reviewer")
review_graph.add_edge(START, "fact_verifier")
review_graph.add_edge(START, "consistency_validator")
review_graph.add_edge(START, "statistical_reviewer")
review_graph.add_edge(START, "reproducibility_reviewer")

# Fan-in from all reviewers to composite quality assessor
review_graph.add_edge("scientific_reviewer", "quality_assessor")
review_graph.add_edge("fact_verifier", "quality_assessor")
review_graph.add_edge("consistency_validator", "quality_assessor")
review_graph.add_edge("statistical_reviewer", "quality_assessor")
review_graph.add_edge("reproducibility_reviewer", "quality_assessor")
review_graph.add_edge("quality_assessor", END)

review_subgraph = review_graph.compile()

__all__ = ["review_subgraph", "review_graph"]
