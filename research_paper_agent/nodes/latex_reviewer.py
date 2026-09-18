"""LaTeX Reviewer — validates and fixes LaTeX compilation errors."""
from __future__ import annotations
import subprocess
import os
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import extract_text_content, llm_fast
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.latex_prompts import LATEX_REVIEWER_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

def _try_compile(tex_path: str) -> tuple[bool, list[str]]:
    """Attempt pdflatex compilation. Returns (success, errors)."""
    try:
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path],
            cwd=os.path.dirname(tex_path),
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            return True, []
        # Extract errors from log
        errors = [l for l in result.stdout.split("\n") if l.startswith("!")]
        return False, errors[:10]
    except FileNotFoundError:
        return False, ["pdflatex not found — install MiKTeX or TeX Live"]
    except subprocess.TimeoutExpired:
        return False, ["pdflatex timed out after 60s"]
    except Exception as exc:
        return False, [str(exc)]

def latex_reviewer_node(state: ResearchPaperState) -> dict:
    node = "latex_reviewer"
    doc = state.get("latex_document", "")
    output_dir = state.get("output_dir", "output/paper")
    tex_path = os.path.join(output_dir, "main.tex")

    if not os.path.exists(tex_path):
        # Write the doc if not already written
        os.makedirs(output_dir, exist_ok=True)
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(doc)

    # Attempt 1: compile
    success, errors = _try_compile(tex_path)
    if success:
        return {"latex_valid": True, "latex_errors": [], "final_tex": doc,
                "execution_log": [make_log_entry(node, "SUCCESS", "compiled on first pass")]}

    # If pdflatex binary is missing entirely, skip futile LLM fix (saves 5-10s and tokens)
    if any("pdflatex not found" in e for e in errors):
        return {
            "latex_valid": False,
            "latex_errors": errors,
            "final_tex": doc,
            "execution_log": [make_log_entry(node, "SKIP", "pdflatex not installed — skipping syntax fix")],
        }

    # Attempt 2: LLM fix + recompile
    try:
        raw_fixed = llm_fast.invoke([
            SystemMessage(content=LATEX_REVIEWER_SYSTEM),
            HumanMessage(content=(
                f"LaTeX document:\n{doc[:8000]}\n\n"
                f"Compilation errors:\n{errors}"
            )),
        ])
        fixed = extract_text_content(raw_fixed.content)

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(fixed)

        success2, errors2 = _try_compile(tex_path)
        if success2:
            return {"latex_valid": True, "latex_errors": [], "final_tex": fixed,
                    "execution_log": [make_log_entry(node, "SUCCESS", "compiled after LLM fix")]}

        return {"latex_valid": False, "latex_errors": errors2, "final_tex": fixed,
                "execution_log": [make_log_entry(node, "PARTIAL", f"errors_remaining={len(errors2)}")]}

    except Exception as exc:
        return {"latex_valid": False, "latex_errors": errors, "final_tex": doc,
                "errors": [make_error_entry(node, exc, fallback_used="original_tex")],
                "execution_log": [make_log_entry(node, "DEGRADED", str(exc))]}
