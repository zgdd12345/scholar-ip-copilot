from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / "plugins" / "scholar-ip" / "workflows"
CAPABILITIES = ROOT / "plugins" / "scholar-ip" / "capabilities"
ROLES = ROOT / "plugins" / "scholar-ip" / "roles" / "modes"
PAPER_TEMPLATE_README = (
    ROOT / "plugins" / "scholar-ip" / "templates" / "paper-project" / "README.md"
)
PAPER_TEMPLATE_ROOT = PAPER_TEMPLATE_README.parent
LAZY_PAPER_FILES = (
    Path(".evidraft/project.yaml"),
    Path(".evidraft/evidence/evidence.jsonl"),
    Path(".evidraft/literature/references.bib"),
    Path("manuscript/main.tex"),
)


def _materialize_lazy_paper_project(tmp_path: Path) -> Path:
    project = tmp_path / "paper"
    for relative in LAZY_PAPER_FILES:
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PAPER_TEMPLATE_ROOT / relative, target)
    return project


def _workflow(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name / "workflow.yaml").read_text(encoding="utf-8"))


def _stage(workflow: str, action: str) -> str:
    return (WORKFLOWS / workflow / "stages" / f"{action}.md").read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _output(action: dict, path: str) -> dict:
    return next(item for item in action["outputs"] if item["path"] == path)


def test_paper_init_creates_only_four_required_core_files_without_overwriting() -> None:
    paper = _workflow("paper")["actions"]["init"]
    stage = _normalized(_stage("paper", "init"))
    template_readme = _normalized(PAPER_TEMPLATE_README.read_text(encoding="utf-8"))
    core_paths = [
        ".evidraft/project.yaml",
        ".evidraft/evidence/evidence.jsonl",
        ".evidraft/literature/references.bib",
        "manuscript/main.tex",
    ]

    assert [output["path"] for output in paper["outputs"]] == [
        *core_paths,
        "manuscript/sections/",
    ]
    assert all(_output(paper, path)["required"] is True for path in core_paths)
    assert _output(paper, "manuscript/sections/")["required"] is False

    for path in core_paths:
        assert path in stage
        assert path in template_readme
    assert "create each missing core file" in stage.lower()
    assert "never overwrite any existing file" in stage.lower()
    assert "leave every existing core file unchanged" in stage.lower()
    assert "update project metadata" not in stage.lower()
    assert "does not create `manuscript/sections/`" in stage.lower()
    assert "creates only four core files" in template_readme.lower()
    assert "later workflow actions create all other artifacts" in template_readme.lower()


def test_lazy_paper_init_materializes_compilable_four_file_graph(tmp_path: Path) -> None:
    project = _materialize_lazy_paper_project(tmp_path)
    actual_files = {
        path.relative_to(project)
        for path in project.rglob("*")
        if path.is_file()
    }
    main = (project / "manuscript/main.tex").read_text(encoding="utf-8")
    guarded_pattern = re.compile(
        r"\\IfFileExists\{([^{}]+\.tex)\}\{\\input\{([^{}]+)\}\}\{\}"
    )
    guarded = set(guarded_pattern.findall(main))
    sections = (
        "sections/introduction",
        "sections/related_work",
        "sections/method",
        "sections/experiments",
        "sections/conclusion",
    )
    failures: list[str] = []

    if actual_files != set(LAZY_PAPER_FILES):
        failures.append(f"unexpected lazy files: {sorted(actual_files)}")
    expected_guards = {(f"{section}.tex", section) for section in sections}
    if guarded != expected_guards:
        failures.append(f"conditional section inputs: {sorted(guarded)}")
    unconditional = guarded_pattern.sub("", main)
    for _command, relative in re.findall(
        r"\\(input|include)\{([^{}]+)\}", unconditional
    ):
        dependency = (project / "manuscript" / relative).with_suffix(".tex")
        if not dependency.is_file():
            failures.append(f"missing unconditional TeX dependency: {relative}")
    for bibliography in re.findall(r"\\bibliography\{([^{}]+)\}", main):
        for relative in bibliography.split(","):
            dependency = (project / "manuscript" / relative.strip()).with_suffix(
                ".bib"
            )
            if not dependency.is_file():
                failures.append(f"missing bibliography: {relative.strip()}")
    if (project / ".evidraft/literature/references.bib").read_bytes() != b"":
        failures.append("canonical bibliography is not empty")

    assert failures == []


@pytest.mark.skipif(shutil.which("latexmk") is None, reason="latexmk is unavailable")
def test_lazy_paper_init_compiles_with_supported_latexmk(tmp_path: Path) -> None:
    project = _materialize_lazy_paper_project(tmp_path)

    result = subprocess.run(
        [
            "latexmk",
            "-pdf",
            "-interaction=nonstopmode",
            "-file-line-error",
            "main.tex",
        ],
        check=False,
        cwd=project / "manuscript",
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
    assert (project / "manuscript/main.pdf").is_file()


def test_patent_init_is_lazy_and_declares_conditional_scaffolding_optional() -> None:
    patent = _workflow("patent")["actions"]["init"]

    assert _output(patent, ".evidraft/project.yaml").get("required", True) is True
    assert all(output.get("required") is False for output in patent["outputs"][1:])

    stage = _normalized(_stage("patent", "init"))
    assert "lazy initialization" in stage.lower()
    assert "do not eagerly create" in stage.lower()
    assert "complete_with_gaps" in stage


@pytest.mark.parametrize("action", ["lit", "idea", "code-audit", "experiment", "review"])
def test_paper_content_stages_are_best_effort_and_reuse_matching_inputs(
    action: str,
) -> None:
    stage = _normalized(_stage("paper", action))

    assert "best effort" in stage.lower()
    assert "Input summary" in stage
    assert "matches the current normalized inputs and source fingerprints" in stage
    assert "reuse" in stage.lower()
    assert "complete_with_gaps" in stage
    assert "blocked" in stage


def test_paper_draft_writes_first_and_consolidates_validation_gaps() -> None:
    action = _workflow("paper")["actions"]["draft"]
    stage = _normalized(_stage("paper", "draft"))
    check = _normalized(_stage("paper", "check"))

    assert "scope" not in action["policies"]
    assert _output(action, ".evidraft/manuscript/validation_gaps.md")["required"] is False
    assert "draft first" in stage.lower()
    assert "scope, evidence, `method_to_code.md`, or prior plan" in stage
    assert "must not block drafting" in stage
    assert ".evidraft/manuscript/validation_gaps.md" in stage
    assert "*.plan.md" not in stage
    assert "*.plan.md" not in check
    assert ".evidraft/manuscript/validation_gaps.md" in check
    assert "Refuse to draft" not in stage


def test_paper_check_has_one_consolidated_verdict_and_venue_continues_with_readiness() -> None:
    check = _normalized(_stage("paper", "check"))
    venue = _normalized(_stage("paper", "venue"))
    venue_action = _workflow("paper")["actions"]["venue"]

    assert check.count("Overall verdict: PASS | WARN | FAIL") == 1
    assert "single consolidated summary" in check.lower()
    assert "missing inputs become findings" in check.lower()
    assert "independent audit work adaptively" in check.lower()

    assert "readiness: PASS | WARN | FAIL" in venue
    assert "continue building the venue bundle" in venue.lower()
    assert "readiness is `WARN` or `FAIL`" in venue
    assert venue_action["policies"] == ["evidence-integrity"]
    assert "compile failure does not block bundle creation" in venue.lower()
    assert "readiness is `warn` or `fail`, or compilation fails" in venue.lower()
    assert "status is `complete_with_gaps`" in venue.lower()
    assert "do **not** auto-submit anywhere" in venue.lower()


@pytest.mark.parametrize("action", ["scout", "prior-art", "disclosure"])
def test_patent_preclaim_stages_are_best_effort(action: str) -> None:
    stage = _normalized(_stage("patent", action))

    assert "best effort" in stage.lower()
    assert "complete_with_gaps" in stage
    assert "blocked" in stage
    assert "missing" in stage.lower()
    assert "gap" in stage.lower()


def test_claims_always_writes_reviewable_text_and_only_structured_outputs_are_optional() -> None:
    action = _workflow("patent")["actions"]["claims"]
    stage = _normalized(_stage("patent", "claims"))

    assert "scope" not in action["policies"]
    assert _output(action, ".evidraft/patent/claims.md").get("required", True) is True
    for path in (
        ".evidraft/patent/claims_parsed.json",
        ".evidraft/patent/claim_chart.md",
        ".evidraft/patent/claim_chart-<ts>.json",
    ):
        assert _output(action, path)["required"] is False

    assert "Always write `claims.md`" in stage
    assert "Drafting risks and gaps" in stage
    assert "parser failure blocks only structured parsing and chart generation" in stage
    assert "registered patent agent / attorney" in stage
    assert "Refuse to draft" not in stage


def test_claims_preserves_existing_attorney_edits_without_explicit_confirmation() -> None:
    stage = _normalized(_stage("patent", "claims"))

    assert "If `claims.md` already exists" in stage
    assert "attorney edits" in stage.lower()
    assert "Never overwrite" in stage
    assert "explicit confirmation" in stage.lower()


def test_claim_parser_exclusively_writes_parsed_claims_before_chart_building() -> None:
    stage = _normalized(_stage("patent", "claims"))

    assert "claim-parser is the sole writer of `claims_parsed.json`" in stage
    assert "claim-chart-builder consumes `claims_parsed.json`" in stage
    assert "writes only `claim_chart.md` and `claim_chart-<ts>.json`" in stage


def test_patent_drafting_roles_preserve_best_effort_generation() -> None:
    claim_drafter = _normalized((ROLES / "claim-drafter.md").read_text(encoding="utf-8"))
    patent_engineer = _normalized((ROLES / "patent-engineer.md").read_text(encoding="utf-8"))

    assert "Refuses to draft when the disclosure is incomplete" not in claim_drafter
    assert "write a one-paragraph refusal" not in claim_drafter
    assert "draft risk-marked placeholders" in claim_drafter
    assert "complete_with_gaps" in claim_drafter
    assert "Refuse to draft a candidate" not in patent_engineer
    assert "preserve all 13 sections with explicit `TODO` gaps" in patent_engineer
    assert "complete_with_gaps" in patent_engineer


def test_patent_review_reuses_matching_inputs_and_emits_one_pass_warn_fail_verdict() -> None:
    stage = _normalized(_stage("patent", "review"))

    assert "Input summary" in stage
    assert "matches the current normalized inputs and source fingerprints" in stage
    assert "reuse" in stage.lower()
    assert stage.count("Overall verdict: PASS | WARN | FAIL") == 1
    assert "READY_FOR_ATTORNEY" not in stage
    assert "NEEDS_WORK" not in stage
    assert "single consolidated summary" in stage.lower()
    assert "review roles adaptively" in stage.lower()


def test_polish_defaults_to_all_without_scope_or_evidence_store_refusal() -> None:
    action = _workflow("polish")["actions"]["run"]
    mode = next(item for item in action["inputs"] if item["name"] == "mode")
    stage = _normalized(_stage("polish", "run"))

    assert action["defaults"]["mode"] == mode["default"] == "all"
    assert "scope" not in action["policies"]
    assert "does not require an EviDraft project, approved scope, or evidence store" in stage
    assert "Refuse if `.evidraft/evidence/evidence.jsonl`" not in stage
    assert "Refuse if `policy:scope`" not in stage
    assert "hunk-level fidelity audit" in stage
    assert "missing evidence store" in stage.lower()


def test_polish_records_all_fidelity_category_verdicts_for_every_hunk() -> None:
    stage = _normalized(_stage("polish", "run"))

    assert "Every hunk receives a fidelity verdict before application" in stage
    for category in ("numbers", "citations", "entities", "hedges"):
        assert f"{category}=PASS|FAIL" in stage
    assert "Only the external evidence-auditor invocation is adaptive" in stage


def test_xreview_is_projectless_without_scope_and_preserves_security_boundaries() -> None:
    action = _workflow("xreview")["actions"]["run"]
    stage = _normalized(_stage("xreview", "run"))

    assert action["policies"] == ["workspace-safety"]
    assert "projectless" in stage.lower()
    assert ".evidraft/project.yaml` is optional" in stage
    assert "approved scope" not in stage.lower()
    assert "no key ever appears in argv" in stage.lower()
    assert "read-only" in stage.lower()
    assert "600 s hard timeout" in stage
    assert "fixed write zone" in stage.lower()
    assert ".evidraft/reviews/" in stage


def test_xreview_refuses_opencode_before_setup_without_claiming_copy_isolation() -> None:
    action = _workflow("xreview")["actions"]["run"]
    stage = _stage("xreview", "run")
    bridge = (
        CAPABILITIES / "code" / "external-agent-bridge" / "spec.md"
    ).read_text(encoding="utf-8")
    agent = next(item for item in action["inputs"] if item["name"] == "agent")
    refusal = "If `agent=opencode`, return `status: blocked` immediately"

    assert "opencode" in agent["values"]
    assert refusal in stage
    assert stage.index(refusal) < stage.index("## Preconditions")
    assert "do not create any review artifact" in stage.lower()
    assert "do not invoke `opencode`" in stage.lower()
    assert "defense in depth" in _normalized(bridge).lower()
    for forbidden in ("Bash:opencode*", "opencode run", "git worktree", "cp -R"):
        assert forbidden not in bridge
        assert forbidden not in stage


def test_external_agent_bridge_uses_adaptive_follow_up_without_fixed_retry() -> None:
    bridge = _normalized(
        (CAPABILITIES / "code" / "external-agent-bridge" / "spec.md").read_text(encoding="utf-8")
    )

    assert "Retry **once**" not in bridge
    assert "no fixed retry count" in bridge.lower()
    assert "recoverable" in bridge.lower()
    assert "quality/error signal" in bridge


def test_all_content_workflow_delegation_is_adaptive() -> None:
    for workflow in ("paper", "patent", "polish", "xreview"):
        router = _normalized((WORKFLOWS / workflow / "SKILL.md").read_text(encoding="utf-8"))
        assert "Delegate adaptively" in router
        assert "no fixed cardinality, waves, or retry count" in router
