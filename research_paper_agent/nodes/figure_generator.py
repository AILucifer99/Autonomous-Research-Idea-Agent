"""Figure Generator — Node 20. Follows existing generate_and_place_images pattern."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
from research_paper_agent.tools import gemini_generate_image_bytes
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.errors import make_error_entry, make_log_entry

def figure_generator_node(state: ResearchPaperState) -> dict:
    """Generate figure files and insert \\includegraphics into the LaTeX body."""
    node = "figure_generator"
    specs = state.get("figure_specs", [])
    merged = state.get("merged_paper_tex", "")
    output_dir = state.get("output_dir", "output/paper")

    if not specs:
        return {"generated_figures": [],
                "execution_log": [make_log_entry(node, "SKIP", "no figures planned")]}

    import concurrent.futures
    import re

    figures_dir = Path(output_dir) / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    generated = []
    errors_list = []

    def _granulate_image_prompt(raw_prompt: str, caption: str = "", description: str = "") -> str:
        """
        Deconstructs and refines large or complex prompts in a granular manner,
        preserving all core technical semantics while tailoring formatting to image model constraints.
        """
        text = raw_prompt.strip()

        # Remove any LaTeX code blocks or markup that confuse image models
        text = re.sub(r"\\[a-zA-Z]+(\{[^}]*\})?", " ", text)
        text = re.sub(r"```[\s\S]*?```", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        # If prompt is compact, return cleaned text with style anchor
        if len(text) <= 320 and len(text.split()) <= 45:
            if "vector" not in text.lower() and "white background" not in text.lower():
                return f"{text}. Clean 2D scientific vector schematic, academic publication illustration, white background, high contrast."
            return text

        # Granular decomposition for oversized prompts:
        # 1. Extract core concept and caption essence
        summary_core = caption or description or text[:120]
        summary_core = summary_core.rstrip(".")

        # 2. Extract key technical nouns / keywords
        words = [w.strip(".,;:()") for w in text.split() if len(w) > 3]
        # Filter common stopwords
        stopwords = {"this", "that", "with", "from", "should", "showing", "figure", "diagram", "please", "generate", "image", "using", "into"}
        keywords = [w for w in words if w.lower() not in stopwords][:12]
        key_components = ", ".join(keywords[:8]) if keywords else summary_core

        # 3. Assemble a granular, semantically faithful visual prompt
        refined = (
            f"Scientific architecture diagram of {summary_core}. "
            f"Key components: {key_components}. "
            f"Horizontal left-to-right modular flow with directional arrows. "
            f"Clean 2D vector schematic, academic paper illustration, white background, crisp typography."
        )
        return refined

    def _generate_single_figure(spec: dict) -> tuple[dict, bool, Optional[str], Optional[Path], Optional[Exception]]:
        fig_id = spec.get("id", 0)
        method = spec.get("generation_method", "gemini_image")
        filename = f"fig_{fig_id}.png"
        filepath = figures_dir / filename
        success = False
        exc_out = None
        raw_prompt = spec.get("prompt", "")
        caption = spec.get("caption", "")
        description = spec.get("description", "")

        if method == "gemini_image" and raw_prompt:
            # Handle prompt granularly
            granular_prompt = _granulate_image_prompt(raw_prompt, caption=caption, description=description)
            try:
                img_bytes = gemini_generate_image_bytes(granular_prompt)
                filepath.write_bytes(img_bytes)
                success = True
            except Exception as exc1:
                # Granular fallback: retry with concise high-level visual prompt preserving semantics
                try:
                    compact_prompt = (
                        f"Clean 2D scientific illustration of {caption or description or 'System Architecture'}. "
                        f"Academic publication style diagram, minimalist layout, white background, high contrast."
                    )
                    img_bytes = gemini_generate_image_bytes(compact_prompt)
                    filepath.write_bytes(img_bytes)
                    success = True
                except Exception as exc2:
                    exc_out = exc2

        elif method in ("tikz", "pgfplots") and spec.get("tikz_code"):
            success = True
            filename = None
        elif method == "table_latex":
            success = True
            filename = None

        return spec, success, filename, filepath if filename else None, exc_out

    # Execute figure generation concurrently
    max_workers = min(4, len(specs)) if len(specs) > 1 else 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(_generate_single_figure, specs))

    # Assemble in original spec order to maintain document layout consistency
    for spec, success, filename, filepath, exc in results:
        fig_id = spec.get("id", 0)
        method = spec.get("generation_method", "gemini_image")
        label = spec.get("label", f"fig:{fig_id}")
        caption = spec.get("caption", "")
        placement = spec.get("placement", "t")

        if exc:
            errors_list.append(make_error_entry(node, exc,
                               fallback_used=f"figure_{fig_id}_placeholder"))

        if filename and success:
            fig_tex = (
                f"\\begin{{figure}}[{placement}]\n"
                f"  \\centering\n"
                f"  \\includegraphics[width=0.9\\linewidth]{{figures/{filename}}}\n"
                f"  \\caption{{{caption}}}\n"
                f"  \\label{{{label}}}\n"
                f"\\end{{figure}}"
            )
            merged += f"\n\n{fig_tex}\n"

        generated.append({
            "figure_id": fig_id,
            "filename": filename or "",
            "path": str(filepath) if filename else "",
            "caption": caption,
            "label": label,
            "generation_method": method,
            "success": success,
            "error": None if success else (str(exc) if exc else "Generation failed"),
        })

    return {
        "merged_paper_tex": merged,
        "generated_figures": generated,
        "errors": errors_list,
        "execution_log": [make_log_entry(node, "SUCCESS",
                          f"generated={sum(1 for g in generated if g['success'])}/{len(specs)}")],
    }
