"""Tests for LaTeX templates."""

from pathlib import Path
from research_paper_agent.config import TARGET_VENUES
from research_paper_agent.nodes.publication_compiler import _load_template

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def test_templates_directory_exists():
    assert TEMPLATES_DIR.exists() and TEMPLATES_DIR.is_dir()


def test_target_venue_templates_exist():
    expected = ["ieee_conference", "ieee_journal", "acm", "springer_lncs", "elsevier", "nature", "arxiv", "generic"]
    for venue in expected:
        tpl_path = TEMPLATES_DIR / f"{venue}.tex"
        assert tpl_path.exists(), f"Template {venue}.tex missing"


def test_template_placeholders():
    required_placeholders = ["%%TITLE%%", "%%ABSTRACT%%", "%%BODY%%"]
    for venue in ["ieee_conference", "arxiv", "generic"]:
        content = _load_template(venue)
        for ph in required_placeholders:
            assert ph in content, f"Placeholder {ph} missing in {venue}.tex"


def test_export_generator_markdown():
    from tempfile import TemporaryDirectory
    from research_paper_agent.nodes.export_generator import export_generator_node

    with TemporaryDirectory() as tmp_dir:
        mock_state = {
            "topic": "Contrastive Graph Learning",
            "paper_type": "technical",
            "target_venue": "ieee_conference",
            "as_of": "2026-09-18",
            "output_dir": tmp_dir,
            "paper_outline": {
                "paper_title": "Contrastive Graph Learning: A Survey",
                "abstract_plan": "This paper investigates contrastive learning on graphs.",
            },
            "merged_paper_tex": (
                r"\section{Introduction}" + "\n"
                r"Graphs are ubiquitous. See \cite{velickovic2018}." + "\n"
                r"\begin{equation}" + "\n"
                r"\mathcal{L} = -\log \frac{\exp(sim(z_i, z_j)/\tau)}{\sum_k \exp(sim(z_i, z_k)/\tau)}" + "\n"
                r"\end{equation}" + "\n"
                r"\begin{figure}[t]" + "\n"
                r"  \centering" + "\n"
                r"  \includegraphics[width=0.9\linewidth]{figures/fig_1.png}" + "\n"
                r"  \caption{Overview Architecture}" + "\n"
                r"  \label{fig:arch}" + "\n"
                r"\end{figure}"
            ),
            "bib_entries": [
                {
                    "key": "velickovic2018",
                    "author": "Velickovic et al.",
                    "title": "Deep Graph Infomax",
                    "year": "2018",
                    "journal": "ICLR",
                }
            ],
            "final_tex": "Mock tex",
            "references_bib": "Mock bib",
        }

        result = export_generator_node(mock_state)
        assert "final_markdown" in result
        assert "final_markdown_path" in result

        md_path = Path(tmp_dir) / "paper.md"
        assert md_path.exists()
        content = md_path.read_text(encoding="utf-8")

        assert "# Contrastive Graph Learning: A Survey" in content
        assert "## Abstract" in content
        assert "## Introduction" in content
        assert "figures/fig_1.png" in content
        assert "## References" in content
        assert "Velickovic et al." in content
