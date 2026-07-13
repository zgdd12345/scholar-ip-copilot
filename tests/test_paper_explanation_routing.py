import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "scholar-ip"
ROUTING_HEADING = "Single-paper explanation routing"


def _single_paper_routing_section() -> str:
    spec = (PLUGIN / "capabilities/research/using-scholar-ip-copilot/spec.md").read_text(
        encoding="utf-8"
    )
    match = re.search(
        rf"(?ms)^### {re.escape(ROUTING_HEADING)}\s*$\n"
        r"(?P<body>.*?)(?=^#{2,3}\s|\Z)",
        spec,
    )
    assert match is not None
    return " ".join(match.group("body").split())


def test_using_routes_unambiguous_single_paper_requests_to_explain() -> None:
    section = _single_paper_routing_section()

    assert (
        "If the user supplies a local PDF, arXiv identifier/URL, DOI, or paper URL and "
        "asks to explain, analyse, close-read, interpret equations, critique, or "
        "produce an academic reading note, recommend `workflow:research.explain`."
    ) in section
    assert (
        "If the user names one uniquely identifiable paper with the same intent, "
        "recommend `workflow:research.explain`."
    ) in section
    for chinese_intent in ("解释论文", "讲解论文", "精读", "公式分析", "学术阅读笔记"):
        assert chinese_intent in section
    assert "Recognise equivalent Chinese intent semantically" in section
    assert (
        "`workflow:using.run` remains read-only: recommend and confirm before invoking."
    ) in section
    assert (
        "If the request is ambiguous between papers, methods, projects, or research "
        "directions, resolve or ask for the specific paper first."
    ) in section
    assert (
        "Route an entire research direction to `workflow:research.deep`, not "
        "`workflow:research.explain`."
    ) in section


def test_public_docs_list_explain_and_its_note_output() -> None:
    root = (ROOT / "README.md").read_text(encoding="utf-8")
    plugin = (PLUGIN / "README.md").read_text(encoding="utf-8")
    command = "$scholar-research explain papers/attention-is-all-you-need.pdf --mode graduate"
    output = ".evidraft/notes/paper-explanations/<paper-slug>.md"

    for text in (root, plugin):
        assert "`guide`, `reading-list`, `explain`, `deep`" in text
        assert command in text
        assert output in text


def test_using_and_research_metadata_describe_the_native_explain_action() -> None:
    using = PLUGIN / "capabilities/research/using-scholar-ip-copilot/spec.md"
    using_metadata = yaml.safe_load(using.read_text(encoding="utf-8").split("---", 2)[1])
    command_map = next(
        item for item in using_metadata["provides"] if "command map" in item
    )
    research_workflow = yaml.safe_load(
        (PLUGIN / "workflows/research/workflow.yaml").read_text(encoding="utf-8")
    )
    research_router = PLUGIN / "workflows/research/SKILL.md"
    router_metadata = yaml.safe_load(
        research_router.read_text(encoding="utf-8").split("---", 2)[1]
    )

    assert "23 current actions" in command_map
    assert "22 frozen v1 mappings" in command_map
    assert "single-paper explanation" in research_workflow["description"]
    assert "single-paper explanation" in router_metadata["description"]
