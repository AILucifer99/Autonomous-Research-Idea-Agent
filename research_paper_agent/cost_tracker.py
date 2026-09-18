"""
Cost and Token Tracking Engine for the Research Paper Agent.

Provides:
- Detailed metrics for each individual LLM and external tool call (tokens, cost, latency).
- Aggregated summary metrics for entire paper generation runs.
- LangChain BaseCallbackHandler integration for automatic zero-overhead call interception.
- Context-managed isolation for concurrent or per-pipeline runs.
"""

from __future__ import annotations

import contextvars
import json
import logging
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from research_paper_agent.config import MODEL_PRICING

logger = logging.getLogger("research_paper_agent.cost_tracker")


@dataclass
class LLMCallMetric:
    """Individual invocation metric."""
    call_id: str
    node_name: str
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    latency_seconds: float
    timestamp: str
    call_type: str = "llm"  # "llm" | "image" | "search"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CostTracker:
    """
    Thread-safe tracker that aggregates token consumption and monetary costs
    for both individual invocations and overall pipeline executions.
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._lock = threading.Lock()
        self._metrics: List[LLMCallMetric] = []
        self._start_time = time.perf_counter()

    def calculate_llm_cost(
        self, model_name: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate USD cost given model and token counts."""
        pricing = MODEL_PRICING.get(model_name)
        if not pricing:
            # Match prefixes e.g. "gemini-2.5-flash-001" -> "gemini-2.5-flash"
            for key, val in MODEL_PRICING.items():
                if key in model_name:
                    pricing = val
                    break
        if not pricing:
            pricing = MODEL_PRICING.get("default", {"input_cost_per_million": 0.15, "output_cost_per_million": 0.60})

        in_rate = pricing.get("input_cost_per_million", 0.15)
        out_rate = pricing.get("output_cost_per_million", 0.60)

        in_cost = (input_tokens / 1_000_000.0) * in_rate
        out_cost = (output_tokens / 1_000_000.0) * out_rate
        return round(in_cost + out_cost, 6)

    def record_llm_call(
        self,
        node_name: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        latency_seconds: float,
        call_id: Optional[str] = None,
    ) -> LLMCallMetric:
        """Record an individual LLM call and calculate cost."""
        total_tokens = input_tokens + output_tokens
        cost_usd = self.calculate_llm_cost(model_name, input_tokens, output_tokens)
        metric = LLMCallMetric(
            call_id=call_id or str(uuid4())[:8],
            node_name=node_name or "unknown_node",
            model_name=model_name or "unknown_model",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            latency_seconds=round(latency_seconds, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
            call_type="llm",
        )
        with self._lock:
            self._metrics.append(metric)

        logger.info(
            "[cost_tracker] LLM call recorded: node=%s model=%s tokens=(in=%d, out=%d, tot=%d) cost=$%.6f latency=%.2fs",
            metric.node_name,
            metric.model_name,
            metric.input_tokens,
            metric.output_tokens,
            metric.total_tokens,
            metric.cost_usd,
            metric.latency_seconds,
        )
        return metric

    def record_tool_call(
        self,
        tool_name: str,
        node_name: str = "tool",
        cost_usd: Optional[float] = None,
        latency_seconds: float = 0.0,
        call_id: Optional[str] = None,
        call_type: str = "tool",
    ) -> LLMCallMetric:
        """Record an external tool call (e.g. image generation or web search)."""
        if cost_usd is None:
            pricing = MODEL_PRICING.get(tool_name, {})
            cost_usd = pricing.get("cost_per_call", 0.0)

        metric = LLMCallMetric(
            call_id=call_id or str(uuid4())[:8],
            node_name=node_name,
            model_name=tool_name,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            cost_usd=round(cost_usd, 6),
            latency_seconds=round(latency_seconds, 3),
            timestamp=datetime.now(timezone.utc).isoformat(),
            call_type=call_type,
        )
        with self._lock:
            self._metrics.append(metric)

        logger.info(
            "[cost_tracker] Tool call recorded: tool=%s node=%s cost=$%.6f latency=%.2fs",
            tool_name,
            node_name,
            metric.cost_usd,
            metric.latency_seconds,
        )
        return metric

    def get_metrics(self) -> List[Dict[str, Any]]:
        """Return a copy of all recorded metrics as dicts."""
        with self._lock:
            return [m.to_dict() for m in self._metrics]

    def get_summary(self) -> Dict[str, Any]:
        """Aggregate total tokens, costs, and breakdown by model and node."""
        with self._lock:
            metrics = list(self._metrics)

        total_cost = sum(m.cost_usd for m in metrics)
        total_in = sum(m.input_tokens for m in metrics)
        total_out = sum(m.output_tokens for m in metrics)
        total_tok = sum(m.total_tokens for m in metrics)
        total_duration = sum(m.latency_seconds for m in metrics)

        by_model: Dict[str, Dict[str, Any]] = {}
        by_node: Dict[str, Dict[str, Any]] = {}

        for m in metrics:
            # Model breakdown
            if m.model_name not in by_model:
                by_model[m.model_name] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                }
            by_model[m.model_name]["calls"] += 1
            by_model[m.model_name]["input_tokens"] += m.input_tokens
            by_model[m.model_name]["output_tokens"] += m.output_tokens
            by_model[m.model_name]["total_tokens"] += m.total_tokens
            by_model[m.model_name]["total_cost_usd"] = round(
                by_model[m.model_name]["total_cost_usd"] + m.cost_usd, 6
            )

            # Node breakdown
            if m.node_name not in by_node:
                by_node[m.node_name] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                }
            by_node[m.node_name]["calls"] += 1
            by_node[m.node_name]["input_tokens"] += m.input_tokens
            by_node[m.node_name]["output_tokens"] += m.output_tokens
            by_node[m.node_name]["total_tokens"] += m.total_tokens
            by_node[m.node_name]["total_cost_usd"] = round(
                by_node[m.node_name]["total_cost_usd"] + m.cost_usd, 6
            )

        return {
            "total_cost_usd": round(total_cost, 6),
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "total_tokens": total_tok,
            "total_calls": len(metrics),
            "total_llm_calls": sum(1 for m in metrics if m.call_type == "llm"),
            "total_image_calls": sum(1 for m in metrics if m.call_type == "image"),
            "total_search_calls": sum(1 for m in metrics if m.call_type == "search"),
            "total_duration_seconds": round(total_duration, 2),
            "by_model": by_model,
            "by_node": by_node,
            "metrics": [m.to_dict() for m in metrics],
        }

    def export_json(self, output_path: str) -> None:
        """Write the summary and metrics to a JSON file."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        summary = self.get_summary()
        p.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    def reset(self) -> None:
        """Clear metrics and reset timer."""
        with self._lock:
            self._metrics.clear()
            self._start_time = time.perf_counter()


# ── Global and Context-Local Tracker Management ──────────────────────

_GLOBAL_TRACKER = CostTracker(name="global")
_CURRENT_TRACKER: contextvars.ContextVar[Optional[CostTracker]] = contextvars.ContextVar(
    "_CURRENT_TRACKER", default=None
)


def get_current_tracker() -> CostTracker:
    """Retrieve the currently active context tracker, or global tracker."""
    tracker = _CURRENT_TRACKER.get()
    return tracker if tracker is not None else _GLOBAL_TRACKER


def set_current_tracker(tracker: Optional[CostTracker]) -> None:
    """Set the active context tracker."""
    _CURRENT_TRACKER.set(tracker)


class CostTrackerSession:
    """
    Context manager to scope tracking to a specific pipeline execution.
    """

    def __init__(self, tracker: Optional[CostTracker] = None):
        self.tracker = tracker or CostTracker(name=f"session_{str(uuid4())[:8]}")
        self._token: Optional[contextvars.Token] = None

    def __enter__(self) -> CostTracker:
        self._token = _CURRENT_TRACKER.set(self.tracker)
        return self.tracker

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token:
            _CURRENT_TRACKER.reset(self._token)


# ── LangChain Callback Handler ────────────────────────────────────────

class CostTrackingCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that listens to LLM lifecycle events,
    measures latency, extracts usage metadata (input/output tokens),
    and records metrics in the active CostTracker.
    """

    def __init__(self, tracker: Optional[CostTracker] = None):
        super().__init__()
        self._tracker = tracker
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    @property
    def tracker(self) -> CostTracker:
        return self._tracker or get_current_tracker()

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Capture invocation start time and invocation context."""
        model_name = "gemini"
        if serialized:
            kwargs_dict = serialized.get("kwargs", {})
            model_name = (
                kwargs_dict.get("model")
                or kwargs_dict.get("model_name")
                or serialized.get("name")
                or model_name
            )

        # Look for node name in metadata or tags
        node_name = "llm_node"
        if metadata and isinstance(metadata, dict):
            node_name = metadata.get("node_name") or metadata.get("langgraph_node") or node_name
            if "model_name" in metadata:
                model_name = metadata["model_name"]
        if tags:
            for tag in tags:
                if tag.startswith("node:"):
                    node_name = tag.split("node:", 1)[1]

        with self._lock:
            self._runs[str(run_id)] = {
                "start_time": time.perf_counter(),
                "model_name": model_name,
                "node_name": node_name,
            }

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Extract usage tokens, calculate latency, and record call metric."""
        with self._lock:
            run_data = self._runs.pop(
                str(run_id),
                {
                    "start_time": time.perf_counter(),
                    "model_name": "gemini",
                    "node_name": "llm_node",
                },
            )

        latency = time.perf_counter() - run_data["start_time"]
        model_name = run_data["model_name"]
        node_name = run_data["node_name"]

        input_tokens = 0
        output_tokens = 0

        # 1. Extract from generations
        if response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    msg = getattr(gen, "message", None)
                    if msg:
                        usage = getattr(msg, "usage_metadata", None)
                        if isinstance(usage, dict):
                            input_tokens += usage.get("input_tokens", 0)
                            output_tokens += usage.get("output_tokens", 0)
                        resp_meta = getattr(msg, "response_metadata", {})
                        if isinstance(resp_meta, dict):
                            if "model_name" in resp_meta and resp_meta["model_name"]:
                                model_name = resp_meta["model_name"]
                            if not input_tokens and "token_usage" in resp_meta:
                                tu = resp_meta["token_usage"]
                                input_tokens += tu.get("prompt_tokens", 0)
                                output_tokens += tu.get("completion_tokens", 0)

        # 2. Extract from response.llm_output fallback
        if not input_tokens and not output_tokens and response.llm_output:
            usage = response.llm_output.get("token_usage") or response.llm_output.get("usage_metadata")
            if isinstance(usage, dict):
                input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
                output_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
            if "model_name" in response.llm_output:
                model_name = response.llm_output["model_name"]

        # 3. Fallback estimate if API did not provide usage metadata
        if input_tokens == 0 and output_tokens == 0:
            # Approximate fallback based on generation text length (~4 chars per token)
            text_out_len = 0
            for gen_list in response.generations or []:
                for gen in gen_list:
                    text_out_len += len(getattr(gen, "text", "") or "")
            output_tokens = max(1, text_out_len // 4)
            input_tokens = max(10, output_tokens // 2)

        self.tracker.record_llm_call(
            node_name=node_name,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_seconds=latency,
            call_id=str(run_id)[:8],
        )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Handle LLM failures gracefully."""
        with self._lock:
            self._runs.pop(str(run_id), None)


# Default singleton callback handler attached to default models
default_cost_callback = CostTrackingCallbackHandler()

__all__ = [
    "LLMCallMetric",
    "CostTracker",
    "CostTrackingCallbackHandler",
    "CostTrackerSession",
    "default_cost_callback",
    "get_current_tracker",
    "set_current_tracker",
]
