"""Figure Planner — Node 15. Follows existing decide_images pattern."""
from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_fast
from research_paper_agent.schemas.design import FigurePlan
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.design_prompts import FIGURE_PLANNER_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def figure_planner_node(state: ResearchPaperState) -> dict:
    node = "figure_planner"
    topic = state.get("topic", "Research Topic")
    try:
        planner = llm_fast.with_structured_output(FigurePlan)
        result = planner.invoke([
            SystemMessage(content=FIGURE_PLANNER_SYSTEM),
            HumanMessage(content=(
                f"Methodology:\n{state.get('methodology', {})}\n\n"
                f"Experiment design:\n{state.get('experiment_design', {})}\n\n"
                f"Math artifacts:\n{state.get('math_artifacts', [])}\n\n"
                f"Topic: {topic}\n"
                f"Target: Plan 4-6 comprehensive figures with clear visual prompts."
            )),
        ])
        specs = [f.model_dump() for f in result.figures]

        # Ensure at least 3 figures exist for rich visual paper presentation
        if len(specs) < 3:
            existing_labels = {s.get("label") for s in specs}
            supplemental = [
                {
                    "id": 101,
                    "figure_type": "architecture",
                    "caption": f"Overall System Architecture for {topic}.",
                    "label": "fig:system_overview",
                    "description": f"High-level block diagram showing the end-to-end processing pipeline for {topic}.",
                    "generation_method": "gemini_image",
                    "prompt": (
                        f"Professional scientific architecture diagram of {topic}. Left-to-right modular pipeline "
                        f"showing input data ingestion, feature encoder, core processing mechanism, and task output heads. "
                        f"Clean 2D vector schematic, academic publication illustration, white background, high contrast, sharp labels."
                    ),
                    "placement": "t",
                },
                {
                    "id": 102,
                    "figure_type": "workflow",
                    "caption": f"Algorithmic Workflow and Training Procedure for {topic}.",
                    "label": "fig:workflow_pipeline",
                    "description": "Step-by-step flowchart illustrating training loop and loss computation.",
                    "generation_method": "gemini_image",
                    "prompt": (
                        f"Scientific flowchart diagram illustrating training workflow for {topic}. "
                        f"Showing forward pass, loss formulation, backpropagation gradient update, and evaluation checkpointing. "
                        f"Minimalist academic vector graphic, white background, clear directional arrows, crisp typography."
                    ),
                    "placement": "t",
                },
                {
                    "id": 103,
                    "figure_type": "comparison",
                    "caption": f"Benchmark Performance Comparison across Baselines for {topic}.",
                    "label": "fig:benchmark_results",
                    "description": "Performance comparison chart against competitive state-of-the-art baselines.",
                    "generation_method": "gemini_image",
                    "prompt": (
                        f"Scientific data visualization chart comparing performance metrics of {topic} against standard baselines. "
                        f"Clean grouped bar chart with error bars, distinct color palette, clean grid lines, white background, legible axis labels."
                    ),
                    "placement": "t",
                },
            ]
            for supp in supplemental:
                if supp["label"] not in existing_labels:
                    specs.append(supp)

        return {"figure_specs": specs,
                "execution_log": [make_log_entry(node, "SUCCESS", f"figures={len(specs)}")]}
    except Exception as exc:
        fallback_specs = [
            {
                "id": 1,
                "figure_type": "architecture",
                "caption": f"Proposed System Architecture for {topic}.",
                "label": "fig:arch_overview",
                "description": f"End-to-end modular architecture for {topic}.",
                "generation_method": "gemini_image",
                "prompt": (
                    f"Scientific architecture diagram of {topic}. Modular layout showing data flow, "
                    f"encoder representations, core attention/transformation layers, and final output. "
                    f"Clean 2D vector illustration, white background, high contrast, academic paper style."
                ),
                "placement": "t",
            },
            {
                "id": 2,
                "figure_type": "workflow",
                "caption": f"Methodological Workflow and Optimization Pipeline for {topic}.",
                "label": "fig:method_pipeline",
                "description": "Sequential process flow diagram from raw input to evaluated predictions.",
                "generation_method": "gemini_image",
                "prompt": (
                    f"Step-by-step scientific flowchart of {topic} methodology. "
                    f"Stages connected with directional arrows, distinct colored stage blocks, "
                    f"clean 2D vector diagram, white background, publication quality."
                ),
                "placement": "t",
            },
            {
                "id": 3,
                "figure_type": "comparison",
                "caption": f"Comparative Performance Evaluation for {topic}.",
                "label": "fig:eval_chart",
                "description": "Comparative benchmark evaluation across efficiency and accuracy metrics.",
                "generation_method": "gemini_image",
                "prompt": (
                    f"Scientific benchmark comparison chart for {topic}. "
                    f"Bar and line plot displaying accuracy vs computational efficiency, "
                    f"academic publication graphics, white background, high resolution."
                ),
                "placement": "t",
            },
        ]
        return {"figure_specs": fallback_specs,
                "errors": [make_error_entry(node, exc, fallback_used="default_figure_suite")],
                "execution_log": [make_log_entry(node, "DEGRADED", str(exc))]}
