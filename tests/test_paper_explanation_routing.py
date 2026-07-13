from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "scholar-ip"


def test_using_routes_unambiguous_single_paper_requests_to_explain() -> None:
    spec = (PLUGIN / "capabilities/research/using-scholar-ip-copilot/spec.md").read_text()
    normalized = " ".join(spec.split())

    for token in (
        "workflow:research.explain",
        "single identifiable paper",
        "local PDF",
        "arXiv",
        "DOI",
        "paper URL",
        "confirm",
        "ambiguous",
        "workflow:research.deep",
    ):
        assert token in spec

    for chinese_intent in ("解释论文", "精读", "公式分析", "学术阅读笔记"):
        assert chinese_intent in spec

    assert "ambiguous between papers, methods, projects, or research directions" in normalized
    assert "Route an entire research direction to `workflow:research.deep`" in normalized
    assert "recommend and confirm before invoking" in normalized


def test_public_docs_list_explain_and_its_note_output() -> None:
    root = (ROOT / "README.md").read_text()
    plugin = (PLUGIN / "README.md").read_text()
    for text in (root, plugin):
        assert "`guide`, `reading-list`, `explain`, `deep`" in text
    assert "`research explain`" in root
    assert ".evidraft/notes/paper-explanations/<paper-slug>.md" in root
