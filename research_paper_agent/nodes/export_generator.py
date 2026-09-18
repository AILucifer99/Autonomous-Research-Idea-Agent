"""Export Generator — compiles final PDF, generates paper.md Markdown, and packages outputs."""
from __future__ import annotations
import subprocess
import os
import re
import shutil
from pathlib import Path
from research_paper_agent.schemas.state import ResearchPaperState
from research_paper_agent.errors import make_error_entry, make_log_entry


def _convert_latex_to_markdown(tex: str) -> str:
    """Transform LaTeX manuscript body into clean GitHub-flavored Markdown."""
    # Remove preamble and document wrapper commands
    tex = re.sub(r"\\documentclass[\s\S]*?\\begin\{document\}", "", tex)
    tex = re.sub(r"\\end\{document\}", "", tex)
    tex = re.sub(r"\\maketitle", "", tex)
    tex = re.sub(r"\\begin\{abstract\}[\s\S]*?\\end\{abstract\}", "", tex)
    tex = re.sub(r"\\bibliography\{[^}]*\}", "", tex)
    tex = re.sub(r"\\bibliographystyle\{[^}]*\}", "", tex)

    # Convert figures to markdown image embeddings
    def _fig_sub(match):
        body = match.group(0)
        img_m = re.search(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", body)
        cap_m = re.search(r"\\caption\{([^}]+)\}", body)
        lbl_m = re.search(r"\\label\{([^}]+)\}", body)
        img_src = img_m.group(1) if img_m else ""
        caption = cap_m.group(1) if cap_m else "Figure"
        label_text = f" ({lbl_m.group(1)})" if lbl_m else ""
        if img_src:
            return f"\n\n![{caption}]({img_src})\n\n*{caption}{label_text}*\n\n"
        return f"\n\n> **[Figure: {caption}]**\n\n"

    tex = re.sub(r"\\begin\{figure\}[\s\S]*?\\end\{figure\}", _fig_sub, tex)

    # Convert math equations to Markdown display math $$...$$
    tex = re.sub(r"\\begin\{equation\}([\s\S]*?)\\end\{equation\}", r"\n$$\n\1\n$$\n", tex)
    tex = re.sub(r"\\begin\{align\*?\}([\s\S]*?)\\end\{align\*?\}", r"\n$$\n\1\n$$\n", tex)

    # Convert sections and headings
    tex = re.sub(r"\\section\*?\{([^}]+)\}", r"\n\n## \1\n\n", tex)
    tex = re.sub(r"\\subsection\*?\{([^}]+)\}", r"\n\n### \1\n\n", tex)
    tex = re.sub(r"\\subsubsection\*?\{([^}]+)\}", r"\n\n#### \1\n\n", tex)
    tex = re.sub(r"\\paragraph\*?\{([^}]+)\}", r"\n\n**\1** ", tex)

    # Convert typography
    tex = re.sub(r"\\textbf\{([^}]+)\}", r"**\1**", tex)
    tex = re.sub(r"\\textit\{([^}]+)\}", r"*\1*", tex)
    tex = re.sub(r"\\emph\{([^}]+)\}", r"*\1*", tex)
    tex = re.sub(r"\\texttt\{([^}]+)\}", r"`\1`", tex)
    tex = re.sub(r"\\cite\{([^}]+)\}", r"[\1]", tex)

    # Convert lists
    tex = re.sub(r"\\begin\{itemize\}", "\n", tex)
    tex = re.sub(r"\\end\{itemize\}", "\n", tex)
    tex = re.sub(r"\\begin\{enumerate\}", "\n", tex)
    tex = re.sub(r"\\end\{enumerate\}", "\n", tex)
    tex = re.sub(r"\\item\s+", "- ", tex)

    # Clean linebreaks and LaTeX comments
    tex = re.sub(r"\\\\(?:\s*\[[^\]]*\])?", "\n", tex)
    tex = re.sub(r"(?<!\\)%.*", "", tex)
    tex = re.sub(r"\n{3,}", "\n\n", tex)
    return tex.strip()


def build_markdown_document(state: ResearchPaperState) -> str:
    """Build a complete, standalone Markdown paper with title, metadata, abstract, body, and references."""
    outline = state.get("paper_outline") or {}
    title = outline.get("paper_title") or state.get("topic", "Research Paper")
    abstract = outline.get("abstract_plan") or ""
    venue = state.get("target_venue", "arxiv").replace("_", " ").title()
    paper_type = state.get("paper_type", "technical").title()
    as_of = state.get("as_of", "")
    bib_entries = state.get("bib_entries", [])
    raw_tex = state.get("merged_paper_tex") or state.get("final_tex") or state.get("latex_document") or ""

    body_md = _convert_latex_to_markdown(raw_tex)

    # Header & metadata
    md_lines = [
        f"# {title}",
        "",
        f"> **Authors:** Autonomous Research Paper Agent  ",
        f"> **Venue Target:** {venue}  ",
        f"> **Manuscript Type:** {paper_type} Paper  ",
        f"> **Date:** {as_of}",
        "",
        "---",
        "",
        "## Abstract",
        "",
        abstract if abstract else f"This paper presents an autonomous scientific study on {state.get('topic', 'the subject')}.",
        "",
        f"**Keywords:** {state.get('topic', 'Artificial Intelligence')}, Autonomous Research, Machine Learning",
        "",
        "---",
        "",
        body_md,
    ]

    # Append formatted References section if bib entries exist
    if bib_entries:
        md_lines.extend(["", "## References", ""])
        for i, e in enumerate(bib_entries, 1):
            author = e.get("author", "Unknown Authors")
            title_e = e.get("title", "Untitled Paper")
            year = e.get("year", "")
            venue_e = e.get("journal") or e.get("booktitle") or "Preprint"
            key = e.get("key", f"ref{i}")
            md_lines.append(f"{i}. **{author}** ({year}). *{title_e}*. In {venue_e}. `[{key}]`\n")

    return "\n".join(md_lines).strip() + "\n"


def export_generator_node(state: ResearchPaperState) -> dict:
    node = "export_generator"
    output_dir = state.get("output_dir", "output/paper")
    tex_path = os.path.join(output_dir, "main.tex")
    bib_path = os.path.join(output_dir, "references.bib")
    pdf_path = os.path.join(output_dir, "main.pdf")
    md_path = os.path.join(output_dir, "paper.md")
    main_md_path = os.path.join(output_dir, "main.md")

    final_tex = state.get("final_tex", state.get("latex_document", ""))
    final_bib = state.get("references_bib", "")

    # Ensure output directories exist
    os.makedirs(output_dir, exist_ok=True)

    # 1. Write LaTeX source and bibliography
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(final_tex)
    with open(bib_path, "w", encoding="utf-8") as f:
        f.write(final_bib)

    # 2. Generate and write complete Markdown paper
    md_content = build_markdown_document(state)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    with open(main_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # 3. Attempt pdflatex compilation (if compiler is available)
    try:
        # pdflatex pass 1
        subprocess.run(["pdflatex", "-interaction=nonstopmode", tex_path],
                       cwd=output_dir, capture_output=True, timeout=60)
        # bibtex
        subprocess.run(["bibtex", "main"],
                       cwd=output_dir, capture_output=True, timeout=30)
        # pdflatex pass 2
        subprocess.run(["pdflatex", "-interaction=nonstopmode", tex_path],
                       cwd=output_dir, capture_output=True, timeout=60)
        # pdflatex pass 3
        subprocess.run(["pdflatex", "-interaction=nonstopmode", tex_path],
                       cwd=output_dir, capture_output=True, timeout=60)

        if os.path.exists(pdf_path):
            return {
                "final_tex": final_tex,
                "final_bib": final_bib,
                "final_pdf_path": pdf_path,
                "final_markdown": md_content,
                "final_markdown_path": md_path,
                "execution_log": [make_log_entry(node, "SUCCESS", f"pdf={pdf_path} md={md_path}")],
            }

        return {
            "final_tex": final_tex,
            "final_bib": final_bib,
            "final_pdf_path": "",
            "final_markdown": md_content,
            "final_markdown_path": md_path,
            "execution_log": [make_log_entry(node, "PARTIAL", f"PDF not generated — .tex & md={md_path} ready")],
        }

    except FileNotFoundError:
        return {
            "final_tex": final_tex,
            "final_bib": final_bib,
            "final_pdf_path": "",
            "final_markdown": md_content,
            "final_markdown_path": md_path,
            "execution_log": [make_log_entry(node, "PARTIAL",
                              f"pdflatex not installed — Markdown ({md_path}) & TeX bundle ready")],
        }
    except Exception as exc:
        return {
            "final_tex": final_tex,
            "final_bib": final_bib,
            "final_pdf_path": "",
            "final_markdown": md_content,
            "final_markdown_path": md_path,
            "errors": [make_error_entry(node, exc, fallback_used="tex_and_md_bundle_only")],
            "execution_log": [make_log_entry(node, "DEGRADED", str(exc))],
        }
