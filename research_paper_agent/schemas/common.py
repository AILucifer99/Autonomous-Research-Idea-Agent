"""
Common / shared base schemas used across the pipeline.

Follows the existing Pydantic BaseModel convention (bwa_backend.py L31-87).
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

__all__ = ["ExecutionError", "AgentOutput"]


class ExecutionError(BaseModel):
    """Structured error entry for the ``errors`` state field."""
    node: str
    type: str = Field(description="retryable | non_retryable | degraded")
    error_class: str = ""
    message: str = ""
    timestamp: str = ""
    retryable: bool = True
    fallback_used: str = ""


class AgentOutput(BaseModel):
    """Optional wrapper to standardise agent outputs (not required by graph)."""
    success: bool = True
    log_entries: List[str] = Field(default_factory=list)
    errors: List[ExecutionError] = Field(default_factory=list)
