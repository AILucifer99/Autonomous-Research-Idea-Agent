"""Knowledge Graph Builder — Node 6."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_fast
from research_paper_agent.schemas.knowledge import KnowledgeGraph
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.knowledge_prompts import KNOWLEDGE_GRAPH_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def knowledge_graph_builder_node(state: ResearchPaperState) -> dict:
    node = "knowledge_graph_builder"
    try:
        builder = llm_fast.with_structured_output(KnowledgeGraph)
        kg = builder.invoke([
            SystemMessage(content=KNOWLEDGE_GRAPH_SYSTEM),
            HumanMessage(content=(
                f"Evidence chunks:\n{state.get('evidence_chunks', [])[:25]}\n\n"
                f"Validated sources:\n{state.get('validated_sources', [])[:15]}"
            )),
        ])
        return {
            "knowledge_graph": kg.model_dump(),
            "execution_log": [make_log_entry(node, "SUCCESS",
                              f"nodes={len(kg.nodes)} edges={len(kg.edges)} clusters={len(kg.clusters)}")],
        }
    except Exception as exc:
        return {
            "knowledge_graph": {"nodes": [], "edges": [], "clusters": []},
            "errors": [make_error_entry(node, exc, fallback_used="empty_graph")],
            "execution_log": [make_log_entry(node, "DEGRADED", str(exc))],
        }
