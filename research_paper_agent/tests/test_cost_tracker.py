"""
Tests for Cost Tracking and Token Accounting System.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from research_paper_agent.cost_tracker import (
    CostTracker,
    CostTrackerSession,
    CostTrackingCallbackHandler,
    get_current_tracker,
)
from research_paper_agent.nodes.traceability_reporter import traceability_reporter_node


def test_cost_calculation():
    tracker = CostTracker(name="test_calc")

    # gemini-2.5-flash: in=0.15/1M, out=0.60/1M
    # 100k in = $0.015, 50k out = $0.030 => $0.045
    cost_flash = tracker.calculate_llm_cost("gemini-2.5-flash", input_tokens=100_000, output_tokens=50_000)
    assert abs(cost_flash - 0.045) < 1e-5

    # gemini-3.5-flash: in=1.25/1M, out=5.00/1M
    # 10k in = $0.0125, 2k out = $0.0100 => $0.0225
    cost_strong = tracker.calculate_llm_cost("gemini-3.5-flash", input_tokens=10_000, output_tokens=2_000)
    assert abs(cost_strong - 0.0225) < 1e-5

    # Tool calls
    img_metric = tracker.record_tool_call(tool_name="gemini-2.5-flash-image", node_name="figure_generator", call_type="image")
    assert img_metric.cost_usd == 0.03
    assert img_metric.call_type == "image"

    search_metric = tracker.record_tool_call(tool_name="tavily_search", node_name="literature_worker", call_type="search")
    assert search_metric.cost_usd == 0.005
    assert search_metric.call_type == "search"


def test_callback_token_recording():
    tracker = CostTracker(name="test_cb")
    handler = CostTrackingCallbackHandler(tracker=tracker)

    run_id = "test-run-123"
    handler.on_llm_start(
        serialized={"kwargs": {"model": "gemini-2.5-flash"}},
        prompts=["Hello world"],
        run_id=run_id,
        metadata={"node_name": "research_planner"},
    )

    ai_msg = AIMessage(
        content="Response here",
        usage_metadata={"input_tokens": 1500, "output_tokens": 400, "total_tokens": 1900},
        response_metadata={"model_name": "gemini-2.5-flash"},
    )
    llm_result = LLMResult(generations=[[ChatGeneration(message=ai_msg)]])

    handler.on_llm_end(llm_result, run_id=run_id)

    metrics = tracker.get_metrics()
    assert len(metrics) == 1
    m = metrics[0]
    assert m["node_name"] == "research_planner"
    assert m["model_name"] == "gemini-2.5-flash"
    assert m["input_tokens"] == 1500
    assert m["output_tokens"] == 400
    assert m["total_tokens"] == 1900
    assert m["cost_usd"] > 0.0


def test_cost_summary_aggregation():
    tracker = CostTracker(name="test_summary")

    tracker.record_llm_call(
        node_name="research_planner",
        model_name="gemini-2.5-flash",
        input_tokens=1000,
        output_tokens=500,
        latency_seconds=1.2,
    )
    tracker.record_llm_call(
        node_name="scientific_reviewer",
        model_name="gemini-3.5-flash",
        input_tokens=5000,
        output_tokens=1000,
        latency_seconds=2.5,
    )
    tracker.record_tool_call(
        tool_name="gemini-2.5-flash-image",
        node_name="figure_generator",
        call_type="image",
    )

    summary = tracker.get_summary()
    assert summary["total_calls"] == 3
    assert summary["total_llm_calls"] == 2
    assert summary["total_image_calls"] == 1
    assert summary["total_input_tokens"] == 6000
    assert summary["total_output_tokens"] == 1500
    assert summary["total_tokens"] == 7500
    assert summary["total_cost_usd"] > 0.0

    assert "gemini-2.5-flash" in summary["by_model"]
    assert "gemini-3.5-flash" in summary["by_model"]
    assert "research_planner" in summary["by_node"]
    assert "scientific_reviewer" in summary["by_node"]


def test_cost_tracker_session():
    outer_tracker = get_current_tracker()
    with CostTrackerSession() as session_tracker:
        current = get_current_tracker()
        assert current is session_tracker
        assert current is not outer_tracker
    # After exit, restored
    assert get_current_tracker() is outer_tracker


def test_json_export():
    tracker = CostTracker(name="test_export")
    tracker.record_llm_call("nodeA", "gemini-2.5-flash", 100, 50, 0.5)

    with TemporaryDirectory() as tmp_dir:
        out_file = Path(tmp_dir) / "cost_summary.json"
        tracker.export_json(str(out_file))

        assert out_file.exists()
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert "total_cost_usd" in data
        assert "by_model" in data
        assert len(data["metrics"]) == 1


def test_traceability_report_with_cost():
    with TemporaryDirectory() as tmp_dir:
        state = {
            "topic": "Neural ODEs",
            "paper_type": "technical",
            "target_venue": "arxiv",
            "errors": [],
            "execution_log": [],
            "quality_scores": {"overall": 8.5, "passes_gate": True},
            "review_feedback": [],
            "validated_sources": [],
            "rejected_sources": [],
            "evidence_chunks": [],
            "citation_report": {"total_citations": 12},
            "revision_count": 0,
            "output_dir": tmp_dir,
            "cost_summary": {
                "total_cost_usd": 0.0425,
                "total_input_tokens": 15000,
                "total_output_tokens": 4000,
                "total_tokens": 19000,
                "total_calls": 5,
                "total_llm_calls": 4,
                "total_image_calls": 1,
                "total_search_calls": 0,
                "total_duration_seconds": 14.5,
                "by_model": {
                    "gemini-2.5-flash": {
                        "calls": 3,
                        "input_tokens": 10000,
                        "output_tokens": 3000,
                        "total_tokens": 13000,
                        "total_cost_usd": 0.0033,
                    },
                    "gemini-3.5-flash": {
                        "calls": 1,
                        "input_tokens": 5000,
                        "output_tokens": 1000,
                        "total_tokens": 6000,
                        "total_cost_usd": 0.01125,
                    },
                },
                "by_node": {
                    "research_planner": {
                        "calls": 1,
                        "input_tokens": 2000,
                        "output_tokens": 500,
                        "total_tokens": 2500,
                        "total_cost_usd": 0.0006,
                    }
                },
            },
        }

        res = traceability_reporter_node(state)
        report = res["traceability_report"]
        assert "## Cost & Token Usage Analysis" in report
        assert "Total Estimated Cost" in report
        assert "### Cost Breakdown by Model" in report
        assert "### Cost Breakdown by Agent Node" in report
        assert (Path(tmp_dir) / "cost_summary.json").exists()
