"""Publication Compiler — assembles complete LaTeX document from template."""
from __future__ import annotations
import os
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from research_paper_agent.llm import llm_fast
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.prompts.latex_prompts import PUBLICATION_COMPILER_SYSTEM
from research_paper_agent.errors import make_error_entry, make_log_entry

# Template paths
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _load_template(venue: str) -> str:
    """Load a LaTeX template file. Fallback to generic."""
    template_file = TEMPLATES_DIR / f"{venue}.tex"
    if not template_file.exists():
        template_file = TEMPLATES_DIR / "generic.tex"
    if template_file.exists():
        return template_file.read_text(encoding="utf-8")
    # Inline fallback
    return (
        "\\documentclass[12pt]{article}\n"
        "\\usepackage{amsmath,amssymb,amsthm,graphicx,hyperref,cite}\n"
        "%%PREAMBLE_EXTRA%%\n"
        "\\begin{document}\n"
        "\\title{%%TITLE%%}\n\\maketitle\n"
        "\\begin{abstract}\n%%ABSTRACT%%\n\\end{abstract}\n"
        "%%BODY%%\n"
        "\\bibliographystyle{plain}\n\\bibliography{references}\n"
        "\\end{document}\n"
    )


def publication_compiler_node(state: ResearchPaperState) -> dict:
    node = "publication_compiler"
    venue = state.get("target_venue", "generic")
    outline = state.get("paper_outline", {})
    merged = state.get("merged_paper_tex", "")
    bib_content = state.get("references_bib", "")

    # Build output directory
    import re
    slug = re.sub(r"[^a-z0-9]+", "_", state.get("topic", "paper").lower())[:50]
    output_dir = os.path.join("output", slug)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "figures"), exist_ok=True)

    try:
        template = _load_template(venue)
        title = outline.get("paper_title", state.get("topic", "Research Paper"))
        abstract = outline.get("abstract_plan", "")

        # Replace placeholders
        doc = template
        doc = doc.replace("%%TITLE%%", title)
        doc = doc.replace("%%AUTHORS%%", "Research Paper Agent")
        doc = doc.replace("%%ABSTRACT%%", abstract)
        doc = doc.replace("%%KEYWORDS%%", state.get("topic", ""))
        doc = doc.replace("%%BODY%%", merged)
        doc = doc.replace("%%PREAMBLE_EXTRA%%", "")
        doc = doc.replace("%%APPENDICES%%", "")

        # Write files
        tex_path = os.path.join(output_dir, "main.tex")
        bib_path = os.path.join(output_dir, "references.bib")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(doc)
        with open(bib_path, "w", encoding="utf-8") as f:
            f.write(bib_content)

        return {
            "latex_document": doc,
            "output_dir": output_dir,
            "execution_log": [make_log_entry(node, "SUCCESS", f"output={output_dir}")],
        }
    except Exception as exc:
        return {
            "latex_document": merged,
            "output_dir": output_dir,
            "errors": [make_error_entry(node, exc, fallback_used="raw_body")],
            "execution_log": [make_log_entry(node, "DEGRADED", str(exc))],
        }
