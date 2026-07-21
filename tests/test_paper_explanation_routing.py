import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "scholar-ip"
ROUTING_HEADING = "Route by intent"


def _single_paper_routing_section() -> str:
    spec = (PLUGIN / "capabilities/research/using-scholar-ip-copilot/spec.md").read_text(
        encoding="utf-8"
    )
    match = re.search(
        rf"(?ms)^## {re.escape(ROUTING_HEADING)}\s*$\n"
        r"(?P<body>.*?)(?=^#{2,3}\s|\Z)",
        spec,
    )
    assert match is not None
    return " ".join(match.group("body").split())


def test_using_routes_unambiguous_single_paper_requests_to_explain() -> None:
    section = _single_paper_routing_section()

    assert "Route unambiguous intent directly" in section
    assert "Explain one identifiable paper | `workflow:research.explain`" in section
    assert "Broad or systematic literature review | `workflow:research.deep`" in section
    assert "Ask one clarifying question only when the request is ambiguous" in section
    assert "Do not add a separate routing confirmation" in section


def test_public_docs_list_explain_and_its_note_output() -> None:
    root = (ROOT / "README.md").read_text(encoding="utf-8")
    plugin = (PLUGIN / "README.md").read_text(encoding="utf-8")
    command = "$scholar-research explain papers/attention-is-all-you-need.pdf --mode graduate"
    output = ".evidraft/notes/paper-explanations/<paper-slug>.md"

    for text in (root, plugin):
        assert "`reading-list`, `explain`, `deep`" in text
        assert command in text
        assert output in text


def test_using_and_research_metadata_describe_the_native_explain_action() -> None:
    using = PLUGIN / "capabilities/research/using-scholar-ip-copilot/spec.md"
    using_metadata = yaml.safe_load(using.read_text(encoding="utf-8").split("---", 2)[1])
    using_text = using.read_text(encoding="utf-8")
    research_workflow = yaml.safe_load(
        (PLUGIN / "workflows/research/workflow.yaml").read_text(encoding="utf-8")
    )
    research_router = PLUGIN / "workflows/research/SKILL.md"
    router_metadata = yaml.safe_load(
        research_router.read_text(encoding="utf-8").split("---", 2)[1]
    )

    assert "current-workflow-map" in using_metadata["provides"]
    assert "direct-intent-routing" in using_metadata["provides"]
    assert "seven public workflows and 22 actions" in " ".join(using_text.split())
    assert "single-paper explanation" in research_workflow["description"]
    assert "single-paper explanation" in router_metadata["description"]
