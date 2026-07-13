"""Contract tests for the EviDraft v2 deterministic core."""

from __future__ import annotations

import json
import multiprocessing
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidraft.core import (  # noqa: E402
    EvidenceError,
    MigrationError,
    PreflightError,
    append_evidence,
    detect_format_version,
    is_sensitive_path,
    migrate_project,
    prune_retention,
    resolve_evidence,
    scope_policy,
    store_snapshot,
    workflow_finalize,
    workflow_preflight,
)
from evidraft.cli import main as cli_main  # noqa: E402
import evidraft.core as core_module  # noqa: E402


def _project_doc(**overrides: object) -> dict:
    doc = {
        "project_type": "paper",
        "title": "Test project",
        "status": {},
        "artifacts": {"evidence": ".evidraft/evidence/evidence.jsonl"},
        "rules": {},
    }
    doc.update(overrides)
    return doc


def _write_project(root: Path, doc: dict | None = None) -> Path:
    path = root / ".evidraft" / "project.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(doc or _project_doc(), sort_keys=False), encoding="utf-8")
    return path


def _evidence_record(**overrides: object) -> dict:
    record = {
        "type": "note",
        "source": "notes:test",
        "claim": "A supported claim.",
        "support": "paragraph 1",
        "confidence": "high",
        "verified": True,
    }
    record.update(overrides)
    return record


def _append_worker(root: str, count: int) -> None:
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from evidraft.core import append_evidence

    for index in range(count):
        append_evidence(Path(root), _evidence_record(claim=f"claim {os.getpid()}-{index}"))


def _hold_migration_lock(root: str, ready: multiprocessing.synchronize.Event) -> None:
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from evidraft.core import _exclusive_lock

    lock = Path(root) / ".evidraft" / ".migration.lock"
    with _exclusive_lock(lock, wait=False):
        ready.set()
        while True:
            __import__("time").sleep(1)


def _hold_append_lock(root: str, ready: multiprocessing.synchronize.Event) -> None:
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from evidraft.core import _process_lock

    lock = Path(root) / ".evidraft" / "evidence" / ".append.lock"
    with _process_lock(lock, wait=False):
        ready.set()
        while True:
            __import__("time").sleep(1)


def _migrate_worker(root: str, results: multiprocessing.queues.Queue) -> None:
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from evidraft.core import migrate_project

    try:
        result = migrate_project(Path(root), wait_for_lock=True)
        results.put(("ok", result.changed))
    except BaseException as exc:
        results.put(("error", type(exc).__name__, str(exc)))


def test_format_version_missing_is_v1_and_explicit_v2_is_v2() -> None:
    assert detect_format_version({}) == 1
    assert detect_format_version({"format_version": 2}) == 2
    with pytest.raises(MigrationError, match="unsupported format_version"):
        detect_format_version({"format_version": 3})


def test_migration_is_transactional_idempotent_and_content_addresses_snapshots(
    tmp_path: Path,
) -> None:
    project_path = _write_project(tmp_path)
    url = "https://example.test/report"
    legacy_rel = Path(".evidraft/literature/snapshots/legacy-url-hash.txt")
    legacy_path = tmp_path / legacy_rel
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_bytes(b"durable source body")

    evidence_path = tmp_path / ".evidraft" / "evidence" / "evidence.jsonl"
    evidence_path.parent.mkdir(parents=True)
    valid = _evidence_record(
        id="ev_0001",
        type="paper",
        source_kind="blog",
        source=url,
        citation_key="report2026",
        file_path=legacy_rel.as_posix(),
        line_range="1:1",
    )
    invalid_raw = '{"id":"ev_0002","type":"paper","citation_key":null}\n'
    missing_snapshot = _evidence_record(
        id="ev_0003",
        type="paper",
        source_kind="blog",
        source="https://example.test/missing",
        citation_key="missing2026",
        file_path=".evidraft/literature/snapshots/missing.txt",
        line_range="1:1",
    )
    missing_raw = json.dumps(missing_snapshot) + "\n"
    evidence_path.write_text(
        json.dumps(valid) + "\n" + invalid_raw + missing_raw,
        encoding="utf-8",
    )
    original_project = project_path.read_bytes()
    original_evidence = evidence_path.read_bytes()

    result = migrate_project(tmp_path)

    assert result.changed is True
    assert result.quarantined == 2
    assert legacy_path.read_bytes() == b"durable source body"
    migrated_project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    assert migrated_project["format_version"] == 2
    migrated_record = json.loads(evidence_path.read_text(encoding="utf-8").strip())
    assert migrated_record["file_path"] != legacy_rel.as_posix()
    assert (tmp_path / migrated_record["file_path"]).read_bytes() == b"durable source body"
    quarantine = tmp_path / ".evidraft" / "evidence" / "quarantine.jsonl"
    assert quarantine.read_text(encoding="utf-8") == invalid_raw + missing_raw

    backups = sorted((tmp_path / ".evidraft" / "backups").iterdir())
    assert len(backups) == 1
    assert (backups[0] / "project.yaml").read_bytes() == original_project
    assert (backups[0] / "evidence" / "evidence.jsonl").read_bytes() == original_evidence

    second = migrate_project(tmp_path)
    assert second.changed is False
    assert len(list((tmp_path / ".evidraft" / "backups").iterdir())) == 1


def test_migration_quarantines_unresolvable_code_evidence_verbatim(tmp_path: Path) -> None:
    _write_project(tmp_path)
    evidence = tmp_path / ".evidraft/evidence/evidence.jsonl"
    evidence.parent.mkdir(parents=True)
    invalid = _evidence_record(
        id="ev_0001",
        type="code",
        source="../outside.py",
        file_path="../outside.py",
        line_range="1:1",
    )
    raw = json.dumps(invalid, separators=(",", ":")) + "\n"
    evidence.write_text(raw, encoding="utf-8")

    result = migrate_project(tmp_path)

    assert result.quarantined == 1
    assert evidence.read_text(encoding="utf-8") == ""
    quarantine = tmp_path / ".evidraft/evidence/quarantine.jsonl"
    assert quarantine.read_text(encoding="utf-8") == raw


def test_failed_migration_leaves_original_project_untouched(tmp_path: Path) -> None:
    project_path = _write_project(tmp_path, _project_doc(title=7))
    before = project_path.read_bytes()

    with pytest.raises(MigrationError, match="schema validation"):
        migrate_project(tmp_path)

    assert project_path.read_bytes() == before
    assert not (tmp_path / ".evidraft" / "project.yaml.tmp").exists()
    assert not (tmp_path / ".evidraft" / ".migration.lock").exists()


def test_migration_rolls_back_keyboard_interrupt_and_retry_preserves_quarantine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_path = _write_project(tmp_path)
    evidence_path = tmp_path / ".evidraft" / "evidence" / "evidence.jsonl"
    evidence_path.parent.mkdir(parents=True)
    invalid_raw = '{"id":"ev_0001","type":"paper","citation_key":null}\n'
    evidence_path.write_text(invalid_raw, encoding="utf-8")
    project_before = project_path.read_bytes()
    evidence_before = evidence_path.read_bytes()
    real_atomic_replace = core_module._atomic_replace
    interrupted = False

    def interrupt_before_commit(path: Path, content: bytes) -> None:
        nonlocal interrupted
        if path == project_path and not interrupted:
            interrupted = True
            raise KeyboardInterrupt
        real_atomic_replace(path, content)

    monkeypatch.setattr(core_module, "_atomic_replace", interrupt_before_commit)
    with pytest.raises(KeyboardInterrupt):
        migrate_project(tmp_path)

    quarantine = tmp_path / ".evidraft" / "evidence" / "quarantine.jsonl"
    assert project_path.read_bytes() == project_before
    assert evidence_path.read_bytes() == evidence_before
    assert not quarantine.exists()

    monkeypatch.setattr(core_module, "_atomic_replace", real_atomic_replace)
    result = migrate_project(tmp_path)
    assert result.quarantined == 1
    assert quarantine.read_text(encoding="utf-8") == invalid_raw


def test_migration_recovers_persistent_journal_after_process_kill(tmp_path: Path) -> None:
    project_path = _write_project(tmp_path)
    evidence_path = tmp_path / ".evidraft" / "evidence" / "evidence.jsonl"
    quarantine = tmp_path / ".evidraft" / "evidence" / "quarantine.jsonl"
    evidence_path.parent.mkdir(parents=True)
    invalid_raw = '{"id":"ev_0001","type":"paper","citation_key":null}\n'
    evidence_path.write_text(invalid_raw, encoding="utf-8")

    backup = tmp_path / ".evidraft" / "backups" / "crashed-transaction"
    (backup / "evidence").mkdir(parents=True)
    (backup / "project.yaml").write_bytes(project_path.read_bytes())
    (backup / "evidence" / "evidence.jsonl").write_bytes(evidence_path.read_bytes())

    # Simulate a hard kill after evidence and quarantine were replaced but before
    # project.yaml became the commit marker. No finally/except handler has run.
    evidence_path.write_bytes(b"")
    quarantine.write_text(invalid_raw, encoding="utf-8")
    journal = tmp_path / ".evidraft" / ".migration-journal.json"
    journal.write_text(
        json.dumps(
            {
                "version": 1,
                "backup_dir": "backups/crashed-transaction",
                "entries": [
                    {
                        "path": "evidence/evidence.jsonl",
                        "existed": True,
                        "replaced": True,
                    },
                    {
                        "path": "evidence/quarantine.jsonl",
                        "existed": False,
                        "replaced": True,
                    },
                    {"path": "project.yaml", "existed": True, "replaced": False},
                ],
            }
        ),
        encoding="utf-8",
    )
    lock = tmp_path / ".evidraft" / ".migration.lock"
    lock.write_text("pid=99999999\n", encoding="utf-8")

    result = migrate_project(tmp_path)

    assert result.changed is True
    assert yaml.safe_load(project_path.read_text(encoding="utf-8"))["format_version"] == 2
    assert evidence_path.read_bytes() == b""
    assert quarantine.read_text(encoding="utf-8") == invalid_raw
    assert not journal.exists()
    assert not lock.exists()


def test_two_hosts_serialize_recovery_and_migration(tmp_path: Path) -> None:
    project_path = _write_project(tmp_path)
    evidence_path = tmp_path / ".evidraft/evidence/evidence.jsonl"
    quarantine = tmp_path / ".evidraft/evidence/quarantine.jsonl"
    evidence_path.parent.mkdir(parents=True)
    invalid_raw = '{ "id": "ev_0001", "type": "paper", "citation_key": null }\n'
    evidence_path.write_text(invalid_raw, encoding="utf-8")
    backup = tmp_path / ".evidraft/backups/two-host-crash"
    (backup / "evidence").mkdir(parents=True)
    (backup / "project.yaml").write_bytes(project_path.read_bytes())
    (backup / "evidence/evidence.jsonl").write_bytes(evidence_path.read_bytes())
    evidence_path.write_bytes(b"")
    quarantine.write_text(invalid_raw, encoding="utf-8")
    (tmp_path / ".evidraft/.migration-journal.json").write_text(
        json.dumps(
            {
                "version": 1,
                "backup_dir": "backups/two-host-crash",
                "entries": [
                    {"path": "evidence/evidence.jsonl", "existed": True, "replaced": True},
                    {
                        "path": "evidence/quarantine.jsonl",
                        "existed": False,
                        "replaced": True,
                    },
                    {"path": "project.yaml", "existed": True, "replaced": False},
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / ".evidraft/.migration.lock").write_text(
        json.dumps({"pid": 99999999, "token": "dead-owner"}) + "\n",
        encoding="utf-8",
    )
    results = multiprocessing.Queue()
    processes = [
        multiprocessing.Process(target=_migrate_worker, args=(str(tmp_path), results))
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=10)
        assert process.exitcode == 0

    outcomes = sorted(results.get(timeout=2) for _ in processes)
    assert outcomes == [("ok", False), ("ok", True)]
    assert quarantine.read_text(encoding="utf-8") == invalid_raw


def test_append_recovers_committed_v2_journal_before_mutating(tmp_path: Path) -> None:
    project_path = _write_project(tmp_path, _project_doc(format_version=2))
    evidence_path = tmp_path / ".evidraft/evidence/evidence.jsonl"
    evidence_path.parent.mkdir(parents=True)
    original = _evidence_record(id="ev_0001", claim="preserve me")
    original_raw = json.dumps(original) + "\n"
    evidence_path.write_text(original_raw, encoding="utf-8")
    backup = tmp_path / ".evidraft/backups/committed-v2-crash"
    (backup / "evidence").mkdir(parents=True)
    (backup / "project.yaml").write_bytes(project_path.read_bytes())
    (backup / "evidence/evidence.jsonl").write_text(original_raw, encoding="utf-8")
    evidence_path.write_bytes(b"")
    (tmp_path / ".evidraft/.migration-journal.json").write_text(
        json.dumps(
            {
                "version": 1,
                "backup_dir": "backups/committed-v2-crash",
                "entries": [
                    {"path": "evidence/evidence.jsonl", "existed": True, "replaced": True},
                    {"path": "project.yaml", "existed": True, "replaced": True},
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / ".evidraft/.migration.lock").write_text(
        json.dumps({"pid": 99999999, "token": "dead-owner"}) + "\n",
        encoding="utf-8",
    )

    appended = append_evidence(tmp_path, _evidence_record(claim="new claim"))

    assert appended["id"] == "ev_0002"
    records = [json.loads(line) for line in evidence_path.read_text().splitlines()]
    assert [record["claim"] for record in records] == ["preserve me", "new claim"]
    assert not (tmp_path / ".evidraft/.migration-journal.json").exists()


@pytest.mark.parametrize(
    ("records", "quarantined_count"),
    [
        ([_evidence_record(id="ev_0001"), _evidence_record(id="ev_0001")], 1),
        ([_evidence_record(id="ev_0001", supersedes="ev_9999")], 1),
        (
            [
                _evidence_record(id="ev_0001"),
                _evidence_record(id="ev_0002", supersedes="ev_0001"),
                _evidence_record(id="ev_0003", supersedes="ev_0001"),
            ],
            1,
        ),
        (
            [
                _evidence_record(id="ev_0001", supersedes="ev_0002"),
                _evidence_record(id="ev_0002", supersedes="ev_0001"),
            ],
            2,
        ),
    ],
    ids=["duplicate-id", "dangling-supersedes", "multiple-successors", "cycle"],
)
def test_migration_quarantines_invalid_graph_rows_preserving_raw_text(
    tmp_path: Path, records: list[dict], quarantined_count: int
) -> None:
    _write_project(tmp_path)
    evidence_path = tmp_path / ".evidraft" / "evidence" / "evidence.jsonl"
    evidence_path.parent.mkdir(parents=True)
    raw_lines = [json.dumps(record, separators=(", ", ": ")) + "\n" for record in records]
    evidence_path.write_text("".join(raw_lines), encoding="utf-8")

    result = migrate_project(tmp_path)

    quarantine = tmp_path / ".evidraft/evidence/quarantine.jsonl"
    quarantined_lines = quarantine.read_text(encoding="utf-8").splitlines(keepends=True)
    assert result.quarantined == quarantined_count
    assert len(quarantined_lines) == quarantined_count
    assert all(line in raw_lines for line in quarantined_lines)
    workflow_preflight(tmp_path, "paper.lit")
    with pytest.raises(PreflightError, match="quarantine"):
        workflow_preflight(tmp_path, "paper.draft")


def test_migration_rejects_corrupt_existing_content_addressed_snapshot(tmp_path: Path) -> None:
    _write_project(tmp_path)
    body = b"authentic body"
    digest = __import__("hashlib").sha256(body).hexdigest()
    legacy = tmp_path / ".evidraft" / "literature" / "snapshots" / "legacy.txt"
    destination = legacy.with_name(f"{digest}.md")
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(body)
    destination.write_bytes(b"corrupt body")
    evidence_path = tmp_path / ".evidraft" / "evidence" / "evidence.jsonl"
    evidence_path.parent.mkdir(parents=True)
    record = _evidence_record(
        id="ev_0001",
        type="paper",
        source_kind="blog",
        source="https://example.test/report",
        citation_key="report2026",
        file_path=legacy.relative_to(tmp_path).as_posix(),
        line_range="1:1",
    )
    evidence_path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    with pytest.raises(MigrationError, match="snapshot.*(corrupt|hash|content)"):
        migrate_project(tmp_path)

    assert yaml.safe_load((tmp_path / ".evidraft/project.yaml").read_text()).get(
        "format_version"
    ) is None
    assert destination.read_bytes() == b"corrupt body"


def test_migration_lock_is_exclusive(tmp_path: Path) -> None:
    _write_project(tmp_path)
    lock = tmp_path / ".evidraft" / ".migration.lock"
    lock.write_text("held", encoding="utf-8")

    with pytest.raises(MigrationError, match="migration.*locked"):
        migrate_project(tmp_path)


def test_migration_rejects_live_owner_then_recovers_sigkill_stale_lock(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    ready = multiprocessing.Event()
    process = multiprocessing.Process(
        target=_hold_migration_lock,
        args=(str(tmp_path), ready),
    )
    process.start()
    try:
        assert ready.wait(timeout=5)
        lock = tmp_path / ".evidraft" / ".migration.lock"
        metadata = json.loads(lock.read_text(encoding="utf-8"))
        assert metadata["pid"] == process.pid
        assert metadata["token"]

        with pytest.raises(MigrationError, match="active|locked"):
            migrate_project(tmp_path)

        process.kill()
        process.join(timeout=5)
        assert process.exitcode is not None and process.exitcode != 0

        result = migrate_project(tmp_path)
        assert result.changed is True
        assert not lock.exists()
    finally:
        if process.is_alive():
            process.kill()
            process.join(timeout=5)


def test_lock_finally_only_releases_its_own_token(tmp_path: Path) -> None:
    lock = tmp_path / ".evidraft" / ".migration.lock"
    manager = core_module._exclusive_lock(lock, wait=False)
    manager.__enter__()
    original = json.loads(lock.read_text(encoding="utf-8"))
    replacement = {"pid": os.getpid(), "token": "replacement-owner"}
    lock.write_text(json.dumps(replacement) + "\n", encoding="utf-8")

    manager.__exit__(None, None, None)

    assert original["token"] != replacement["token"]
    assert json.loads(lock.read_text(encoding="utf-8")) == replacement


def test_evidence_append_is_process_safe_and_allocates_sequential_ids(tmp_path: Path) -> None:
    # All workers observe v1 initially. Exactly one migrates while the others wait,
    # then all append through the independent evidence lock.
    _write_project(tmp_path)
    processes = [multiprocessing.Process(target=_append_worker, args=(str(tmp_path), 5)) for _ in range(3)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=15)
        assert process.exitcode == 0

    evidence_path = tmp_path / ".evidraft" / "evidence" / "evidence.jsonl"
    records = [json.loads(line) for line in evidence_path.read_text(encoding="utf-8").splitlines()]
    assert [record["id"] for record in records] == [f"ev_{i:04d}" for i in range(1, 16)]
    assert len({record["claim"] for record in records}) == 15
    assert yaml.safe_load((tmp_path / ".evidraft" / "project.yaml").read_text())["format_version"] == 2
    assert len(list((tmp_path / ".evidraft" / "backups").iterdir())) == 1


def test_evidence_append_recovers_sigkill_stale_owner(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    ready = multiprocessing.Event()
    process = multiprocessing.Process(target=_hold_append_lock, args=(str(tmp_path), ready))
    writers: list[multiprocessing.Process] = []
    process.start()
    try:
        assert ready.wait(timeout=5)
        lock = tmp_path / ".evidraft/evidence/.append.lock"
        original_inode = lock.stat().st_ino
        writers = [
            multiprocessing.Process(target=_append_worker, args=(str(tmp_path), 3))
            for _ in range(2)
        ]
        for writer in writers:
            writer.start()
        __import__("time").sleep(0.1)
        assert all(writer.is_alive() for writer in writers)
        assert lock.stat().st_ino == original_inode

        process.kill()
        process.join(timeout=5)
        assert process.exitcode is not None and process.exitcode != 0
        for writer in writers:
            writer.join(timeout=10)
            assert writer.exitcode == 0
        records = [
            json.loads(line)
            for line in (tmp_path / ".evidraft/evidence/evidence.jsonl")
            .read_text()
            .splitlines()
        ]
        assert [record["id"] for record in records] == [f"ev_{index:04d}" for index in range(1, 7)]
        assert lock.exists()
        assert lock.stat().st_ino == original_inode
    finally:
        if process.is_alive():
            process.kill()
            process.join(timeout=5)
        for writer in writers:
            if writer.is_alive():
                writer.kill()
                writer.join(timeout=5)


def test_evidence_append_validates_records_and_supersedes_target(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    first = append_evidence(tmp_path, _evidence_record())
    assert first["id"] == "ev_0001"

    with pytest.raises(EvidenceError, match="schema validation"):
        append_evidence(
            tmp_path,
            _evidence_record(type="paper", source="doi:10.1/test", citation_key=None),
        )
    with pytest.raises(EvidenceError, match="does not exist"):
        append_evidence(tmp_path, _evidence_record(supersedes="ev_9999"))


def test_evidence_append_rejects_second_superseder(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    first = append_evidence(tmp_path, _evidence_record())
    append_evidence(tmp_path, _evidence_record(supersedes=first["id"]))

    with pytest.raises(EvidenceError, match="already superseded"):
        append_evidence(tmp_path, _evidence_record(supersedes=first["id"]))


def test_evidence_append_requires_valid_content_addressed_web_snapshot(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    body = b"web source"
    digest = __import__("hashlib").sha256(body).hexdigest()
    relative = Path(".evidraft/literature/snapshots") / f"{digest}.md"
    record = _evidence_record(
        type="paper",
        source_kind="blog",
        source="https://example.test/source",
        citation_key="source2026",
        file_path=relative.as_posix(),
        line_range="1:1",
    )

    with pytest.raises(EvidenceError, match="snapshot.*does not exist"):
        append_evidence(tmp_path, record)
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(b"tampered")
    with pytest.raises(EvidenceError, match="snapshot.*hash"):
        append_evidence(tmp_path, record)
    path.write_bytes(body)
    assert append_evidence(tmp_path, record)["id"] == "ev_0001"


def test_web_snapshot_rejects_symlinked_store(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    body = b"external web source"
    digest = __import__("hashlib").sha256(body).hexdigest()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / f"{digest}.md").write_bytes(body)
    snapshots = tmp_path / ".evidraft/literature/snapshots"
    snapshots.parent.mkdir(parents=True)
    snapshots.symlink_to(outside, target_is_directory=True)

    with pytest.raises(EvidenceError, match="symlink"):
        append_evidence(
            tmp_path,
            _evidence_record(
                type="paper",
                source_kind="blog",
                source="https://example.test/external",
                citation_key="external2026",
                file_path=f".evidraft/literature/snapshots/{digest}.md",
                line_range="1:1",
            ),
        )


@pytest.mark.parametrize("record_type", ["code", "experiment"])
def test_code_and_experiment_evidence_require_confined_resolvable_lines(
    tmp_path: Path, record_type: str
) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    source = tmp_path / "artifacts" / "source.txt"
    source.parent.mkdir()
    source.write_text("one\ntwo\n", encoding="utf-8")
    base = _evidence_record(
        type=record_type,
        source="artifacts/source.txt",
        file_path="artifacts/source.txt",
        line_range="1:2",
    )

    assert append_evidence(tmp_path, base)["id"] == "ev_0001"
    with pytest.raises(EvidenceError, match="project-relative|traversal"):
        append_evidence(tmp_path, {**base, "file_path": "../outside.txt"})
    with pytest.raises(EvidenceError, match="does not exist"):
        append_evidence(tmp_path, {**base, "file_path": "artifacts/missing.txt"})
    with pytest.raises(EvidenceError, match="out of bounds"):
        append_evidence(tmp_path, {**base, "line_range": "2:3"})


def test_preflight_migrates_v1_before_the_action_can_write(tmp_path: Path) -> None:
    project = _write_project(tmp_path)

    result = workflow_preflight(tmp_path, "paper.lit")

    assert result.scope == "pass"
    assert yaml.safe_load(project.read_text(encoding="utf-8"))["format_version"] == 2


def test_projectless_note_preflight_preserves_default_workspace_safety(tmp_path: Path) -> None:
    explanation = workflow_preflight(
        tmp_path,
        "research.explain",
        target_paths=[".evidraft/notes/paper-explanations/paper.md"],
    )
    reading_list = workflow_preflight(
        tmp_path,
        "research.reading-list",
        target_paths=[".evidraft/notes/topic-2026-07-13.md"],
    )

    assert explanation.scope == reading_list.scope == "pass"
    assert not (tmp_path / ".evidraft/project.yaml").exists()
    with pytest.raises(PreflightError, match="sensitive"):
        workflow_preflight(tmp_path, "research.explain", target_paths=[".env.local"])
    with pytest.raises(PreflightError, match="project root"):
        workflow_preflight(tmp_path, "research.explain", target_paths=["../outside.md"])
    with pytest.raises(PreflightError, match="project migration"):
        workflow_preflight(tmp_path, "paper.lit", target_paths=["notes/lit.md"])

    descriptor_root = tmp_path / "descriptor-project"
    project = _write_project(
        descriptor_root,
        _project_doc(safety={"forbidden_paths": ["private/**"]}),
    )
    with pytest.raises(PreflightError, match="sensitive"):
        workflow_preflight(
            descriptor_root,
            "research.explain",
            target_paths=["private/paper.md"],
        )
    assert yaml.safe_load(project.read_text(encoding="utf-8"))["format_version"] == 2


def test_resolve_requires_verified_evidence_and_follows_supersedes(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    first = append_evidence(tmp_path, _evidence_record(verified=False))
    latest = append_evidence(tmp_path, _evidence_record(supersedes=first["id"]))

    assert resolve_evidence(tmp_path, first["id"])["id"] == latest["id"]
    with pytest.raises(EvidenceError, match="not verified"):
        resolve_evidence(tmp_path, first["id"], follow_supersedes=False)
    with pytest.raises(EvidenceError, match="does not exist"):
        resolve_evidence(tmp_path, "ev_9999")


def test_resolve_rejects_supersedes_cycles(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    evidence_path = tmp_path / ".evidraft" / "evidence" / "evidence.jsonl"
    evidence_path.parent.mkdir(parents=True)
    one = _evidence_record(id="ev_0001", supersedes="ev_0002")
    two = _evidence_record(id="ev_0002", supersedes="ev_0001")
    evidence_path.write_text(json.dumps(one) + "\n" + json.dumps(two) + "\n", encoding="utf-8")

    with pytest.raises(EvidenceError, match="cycle"):
        resolve_evidence(tmp_path, "ev_0001")


def test_resolve_revalidates_final_snapshot_storage(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    body = b"durable web source"
    snapshot = store_snapshot(tmp_path, "https://example.test/source", body)
    record = append_evidence(
        tmp_path,
        _evidence_record(
            type="paper",
            source_kind="blog",
            source="https://example.test/source",
            citation_key="source2026",
            file_path=snapshot.relative_to(tmp_path).as_posix(),
            line_range="1:1",
        ),
    )
    snapshot.unlink()
    with pytest.raises(EvidenceError, match="snapshot.*does not exist"):
        resolve_evidence(tmp_path, record["id"])
    snapshot.write_bytes(b"tampered")
    with pytest.raises(EvidenceError, match="snapshot.*hash"):
        resolve_evidence(tmp_path, record["id"])


def test_resolve_rejects_symlinked_evidraft_and_escaping_evidence_path(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    _write_project(outside, _project_doc(format_version=2))
    evidence = outside / ".evidraft/evidence/evidence.jsonl"
    evidence.parent.mkdir(parents=True)
    evidence.write_text(json.dumps(_evidence_record(id="ev_0001")) + "\n")
    root = tmp_path / "project"
    root.mkdir()
    (root / ".evidraft").symlink_to(outside / ".evidraft", target_is_directory=True)
    with pytest.raises(EvidenceError, match="symlink|escapes"):
        resolve_evidence(root, "ev_0001")

    safe = tmp_path / "safe"
    _write_project(safe, _project_doc(format_version=2))
    escaped = tmp_path / "escaped-evidence"
    escaped.mkdir()
    (escaped / "evidence.jsonl").write_text(
        json.dumps(_evidence_record(id="ev_0001")) + "\n"
    )
    (safe / ".evidraft/evidence").symlink_to(escaped, target_is_directory=True)
    with pytest.raises(EvidenceError, match="symlink|escapes"):
        resolve_evidence(safe, "ev_0001")


def test_preflight_validates_complete_graph_and_required_current_evidence(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    evidence_path = tmp_path / ".evidraft/evidence/evidence.jsonl"
    evidence_path.parent.mkdir(parents=True)
    one = _evidence_record(id="ev_0001", verified=True)
    two = _evidence_record(id="ev_0002", supersedes="ev_0001", verified=True)
    evidence_path.write_text(json.dumps(one) + "\n" + json.dumps(two) + "\n", encoding="utf-8")

    with pytest.raises(PreflightError, match="superseded"):
        workflow_preflight(tmp_path, "paper.lit", evidence_ids=["ev_0001"])
    assert workflow_preflight(tmp_path, "paper.lit", evidence_ids=["ev_0002"]).scope == "pass"
    two["verified"] = False
    evidence_path.write_text(json.dumps(one) + "\n" + json.dumps(two) + "\n", encoding="utf-8")
    with pytest.raises(PreflightError, match="not verified"):
        workflow_preflight(tmp_path, "paper.lit", evidence_ids=["ev_0002"])

    dangling = _evidence_record(id="ev_0003", supersedes="ev_9999")
    evidence_path.write_text(json.dumps(dangling) + "\n", encoding="utf-8")
    with pytest.raises(PreflightError, match="supersedes"):
        workflow_preflight(tmp_path, "paper.lit")


def test_preflight_revalidates_current_snapshot_hash(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    body = b"current source"
    snapshot = store_snapshot(tmp_path, "https://example.test/current", body)
    record = append_evidence(
        tmp_path,
        _evidence_record(
            type="paper",
            source_kind="blog",
            source="https://example.test/current",
            citation_key="current2026",
            file_path=snapshot.relative_to(tmp_path).as_posix(),
            line_range="1:1",
        ),
    )
    snapshot.write_bytes(b"tampered")
    with pytest.raises(PreflightError, match="snapshot.*hash"):
        workflow_preflight(tmp_path, "paper.lit", evidence_ids=[record["id"]])


def test_snapshot_store_uses_body_sha256_not_url(tmp_path: Path) -> None:
    _write_project(tmp_path)
    first = store_snapshot(tmp_path, "https://example.test/same", b"version one")
    repeated = store_snapshot(tmp_path, "https://example.test/same", b"version one")
    changed = store_snapshot(tmp_path, "https://example.test/same", b"version two")

    assert first == repeated
    assert first != changed
    assert first.name == "197c7c60ef8a8470a38d1a9212bdfde9cfe6fd4be910825fe6ac7880ac765d16.md"
    assert first.read_bytes() == b"version one"
    assert changed.read_bytes() == b"version two"
    assert yaml.safe_load((tmp_path / ".evidraft/project.yaml").read_text())["format_version"] == 2


def test_core_rejects_symlinked_evidraft_and_escaping_internal_paths(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    _write_project(outside, _project_doc(format_version=2))
    (root / ".evidraft").symlink_to(outside / ".evidraft", target_is_directory=True)

    with pytest.raises((MigrationError, EvidenceError), match="symlink|escapes"):
        migrate_project(root)
    with pytest.raises((MigrationError, EvidenceError), match="symlink|escapes"):
        append_evidence(root, _evidence_record())
    with pytest.raises((MigrationError, EvidenceError), match="symlink|escapes"):
        store_snapshot(root, "https://example.test/source", b"source")

    safe_root = tmp_path / "safe-project"
    _write_project(safe_root, _project_doc(format_version=2))
    escaped_evidence = tmp_path / "escaped-evidence"
    escaped_evidence.mkdir()
    (safe_root / ".evidraft/evidence").symlink_to(escaped_evidence, target_is_directory=True)
    with pytest.raises(EvidenceError, match="symlink|escapes"):
        append_evidence(safe_root, _evidence_record())

    escaped_snapshots = tmp_path / "escaped-snapshots"
    escaped_snapshots.mkdir()
    snapshots_parent = safe_root / ".evidraft/literature"
    snapshots_parent.mkdir()
    (snapshots_parent / "snapshots").symlink_to(escaped_snapshots, target_is_directory=True)
    with pytest.raises(EvidenceError, match="symlink|escapes"):
        store_snapshot(safe_root, "https://example.test/source", b"source")

    inside_root = tmp_path / "inside-project"
    _write_project(inside_root, _project_doc(format_version=2))
    redirected = inside_root / "redirected"
    redirected.mkdir()
    (inside_root / ".evidraft/evidence").symlink_to(
        redirected, target_is_directory=True
    )
    with pytest.raises(EvidenceError, match="symlink"):
        append_evidence(inside_root, _evidence_record())
    assert not (redirected / "evidence.jsonl").exists()


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        ("paper.draft", "block"),
        ("patent.claims", "block"),
        ("polish.run", "block"),
        ("paper.idea", "warn"),
        ("patent.scout", "warn"),
        ("research.deep", "warn"),
        ("paper.lit", "pass"),
    ],
)
def test_scope_policy_uses_canonical_operation_ids(operation: str, expected: str) -> None:
    assert scope_policy(operation) == expected


@pytest.mark.parametrize(
    "path",
    [".env", "config/.env.local", "secrets/token.txt", "credentials.json", "keys/a.pem", "a.key", ".ssh/id_rsa.pub"],
)
def test_workspace_safety_detects_sensitive_paths(path: str) -> None:
    assert is_sensitive_path(path)


def test_workspace_safety_allows_similar_non_sensitive_paths() -> None:
    assert not is_sensitive_path("docs/environment.md")
    assert not is_sensitive_path("keynote/slides.keynote")


def test_publish_preflight_blocks_quarantine_and_sensitive_targets(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    quarantine = tmp_path / ".evidraft" / "evidence" / "quarantine.jsonl"
    quarantine.parent.mkdir(parents=True)
    quarantine.write_text("bad evidence\n", encoding="utf-8")

    with pytest.raises(PreflightError, match="quarantine"):
        workflow_preflight(tmp_path, "paper.draft")
    quarantine.write_text("", encoding="utf-8")
    with pytest.raises(PreflightError, match="sensitive"):
        workflow_preflight(tmp_path, "paper.lit", target_paths=[".env.local"])

    result = workflow_preflight(tmp_path, "paper.lit", target_paths=["notes/lit.md"])
    assert result.scope == "pass"


def test_preflight_resolves_targets_within_root_and_external_write_zone(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    outside = tmp_path.parent / "outside.md"

    for target in (outside, "../outside.md"):
        with pytest.raises(PreflightError, match="project root"):
            workflow_preflight(tmp_path, "paper.lit", target_paths=[target])

    result = workflow_preflight(
        tmp_path,
        "paper.lit",
        target_paths=[".evidraft/reviews/review.md"],
        write_zone=".evidraft/reviews",
    )
    assert result.scope == "pass"
    with pytest.raises(PreflightError, match="write zone"):
        workflow_preflight(
            tmp_path,
            "paper.lit",
            target_paths=["manuscript/main.tex"],
            write_zone=".evidraft/reviews",
        )


def test_xreview_preflight_enforces_derived_write_zone(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    with pytest.raises(PreflightError, match="target.*required|write zone"):
        workflow_preflight(tmp_path, "xreview.run")
    with pytest.raises(PreflightError, match="write zone"):
        workflow_preflight(
            tmp_path,
            "xreview.run",
            target_paths=["manuscript/main.tex"],
            write_zone=".",
        )
    result = workflow_preflight(
        tmp_path,
        "xreview.run",
        target_paths=[".evidraft/reviews/report.md"],
    )
    assert result.scope == "pass"


def test_xreview_preflight_separates_read_target_from_write_output(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    manuscript = tmp_path / "manuscript" / "main.tex"
    manuscript.parent.mkdir()
    manuscript.write_text("review me")

    result = workflow_preflight(
        tmp_path,
        "xreview.run",
        read_paths=["manuscript/main.tex"],
        target_paths=[".evidraft/reviews/report.md"],
    )
    assert result.scope == "pass"
    with pytest.raises(PreflightError, match="sensitive"):
        workflow_preflight(
            tmp_path,
            "xreview.run",
            read_paths=[".env"],
            target_paths=[".evidraft/reviews/report.md"],
        )


@pytest.mark.parametrize("nested", [False, True], ids=["zone", "nested-component"])
def test_xreview_rejects_symlinked_write_zone_components(tmp_path: Path, nested: bool) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    reviews = tmp_path / ".evidraft/reviews"
    actual = tmp_path / ".evidraft/actual-reviews"
    actual.mkdir(parents=True)
    if nested:
        reviews.mkdir()
        (reviews / "nested").symlink_to(actual, target_is_directory=True)
        target = ".evidraft/reviews/nested/report.md"
    else:
        reviews.symlink_to(actual, target_is_directory=True)
        target = ".evidraft/reviews/report.md"

    with pytest.raises(PreflightError, match="symlink"):
        workflow_preflight(tmp_path, "xreview.run", target_paths=[target])


def _write_scope(root: Path, name: str, frontmatter: dict, body: str = "") -> Path:
    path = root / ".evidraft" / "scope" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n" + body,
        encoding="utf-8",
    )
    return path


def test_preflight_parses_scope_frontmatter_and_enforces_freshness(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    _write_scope(
        tmp_path,
        "2026-07-12-topic.md",
        {"status": "draft", "approved_date": "2026-07-12"},
        body="status: approved\napproved_date: 2026-07-12\n",
    )
    with pytest.raises(PreflightError, match="scope"):
        workflow_preflight(tmp_path, "paper.draft", today=date(2026, 7, 12))

    _write_scope(
        tmp_path,
        "2026-07-13-topic.md",
        {"status": "approved", "approved_date": "2026-06-27"},
    )
    with pytest.raises(PreflightError, match="stale"):
        workflow_preflight(tmp_path, "paper.draft", today=date(2026, 7, 12))

    _write_scope(
        tmp_path,
        "2026-07-14-topic.md",
        {"status": "approved", "approved_date": "2026-06-28"},
    )
    assert workflow_preflight(tmp_path, "paper.draft", today=date(2026, 7, 12)).warnings == ()


@pytest.mark.parametrize("link_kind", ["directory", "file"])
def test_scope_policy_rejects_symlinked_scope_content(tmp_path: Path, link_kind: str) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    external = tmp_path / "external-scope"
    approved = external / "2026-07-12-approved.md"
    approved.parent.mkdir(parents=True)
    approved.write_text(
        "---\nstatus: approved\napproved_date: 2026-07-12\n---\n",
        encoding="utf-8",
    )
    scope_dir = tmp_path / ".evidraft/scope"
    if link_kind == "directory":
        scope_dir.symlink_to(external, target_is_directory=True)
    else:
        scope_dir.mkdir()
        (scope_dir / approved.name).symlink_to(approved)

    with pytest.raises(PreflightError, match="symlink|escapes"):
        workflow_preflight(tmp_path, "paper.draft", today=date(2026, 7, 12))


@pytest.mark.parametrize("override", ["disabled", "warn", "block", "enabled"])
def test_preflight_ignores_legacy_hook_override_for_canonical_block(
    tmp_path: Path, override: str
) -> None:
    _write_project(
        tmp_path,
        _project_doc(format_version=2, hooks={"scope_required": override}),
    )

    with pytest.raises(PreflightError, match="scope"):
        workflow_preflight(tmp_path, "paper.draft", today=date(2026, 7, 12))


def test_preflight_ignores_legacy_hook_override_for_canonical_warn(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        _project_doc(format_version=2, hooks={"scope_required": "block"}),
    )

    result = workflow_preflight(tmp_path, "paper.idea", today=date(2026, 7, 12))

    assert result.scope == "warn"
    assert result.warnings


def test_preflight_uses_project_scope_staleness_days(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        _project_doc(format_version=2, scope={"staleness_days": 30}),
    )
    _write_scope(
        tmp_path,
        "2026-07-12-topic.md",
        {"status": "approved", "approved_date": "2026-06-20"},
    )
    assert workflow_preflight(tmp_path, "paper.draft", today=date(2026, 7, 12)).warnings == ()


def test_preflight_short_circuits_scope_reads_when_policy_does_not_run(tmp_path: Path) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    scope = tmp_path / ".evidraft" / "scope" / "2026-07-12-corrupt.md"
    scope.parent.mkdir(parents=True)
    scope.write_bytes(b"\xff\xfe\x00")

    result = workflow_preflight(tmp_path, "paper.lit", today=date(2026, 7, 12))

    assert result.scope == "pass"
    assert result.warnings == ()


def test_preflight_uses_project_defined_forbidden_paths(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        _project_doc(
            format_version=2,
            safety={"forbidden_paths": ["private/**", "*.token"]},
        ),
    )

    for target in ("private/report.md", "access.token"):
        with pytest.raises(PreflightError, match="sensitive"):
            workflow_preflight(tmp_path, "paper.lit", target_paths=[target])


def test_retention_prunes_by_age_then_count_without_following_symlinks(tmp_path: Path) -> None:
    now = datetime(2026, 7, 12, tzinfo=timezone.utc)
    paths = []
    for index, days_old in enumerate((1, 2, 3, 20), start=1):
        path = tmp_path / f"review-{index}.md"
        path.write_text(str(index), encoding="utf-8")
        timestamp = (now - timedelta(days=days_old)).timestamp()
        os.utime(path, (timestamp, timestamp))
        paths.append(path)
    outside = tmp_path.parent / "outside-review.md"
    outside.write_text("outside", encoding="utf-8")
    (tmp_path / "review-link.md").symlink_to(outside)

    removed = prune_retention(
        tmp_path,
        pattern="review-*.md",
        keep_last=2,
        max_age_days=10,
        now=now,
    )

    assert {path.name for path in removed} == {"review-3.md", "review-4.md"}
    assert paths[0].exists() and paths[1].exists()
    assert (tmp_path / "review-link.md").is_symlink()
    assert outside.exists()


def test_retention_rejects_traversal_and_never_prunes_symlinked_directory(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    _write_project(root, _project_doc(format_version=2))
    directory = root / ".evidraft" / "reviews"
    directory.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    for name in ("one.md", "two.md"):
        (outside / name).write_text(name, encoding="utf-8")
    (directory / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="relative|traversal"):
        workflow_finalize(root, retention={"directory": str(directory), "keep_last": 1})
    with pytest.raises(ValueError, match="escapes|traversal"):
        workflow_finalize(root, retention={"directory": "../outside", "keep_last": 1})
    with pytest.raises(ValueError, match="pattern.*traversal"):
        prune_retention(directory, pattern="../*.md", keep_last=1)

    assert prune_retention(directory, pattern="linked/*.md", keep_last=1) == ()
    assert sorted(path.name for path in outside.iterdir()) == ["one.md", "two.md"]


def test_workflow_finalize_applies_declared_retention(tmp_path: Path) -> None:
    _write_project(tmp_path)
    output_dir = tmp_path / ".evidraft" / "reviews"
    output_dir.mkdir(parents=True)
    for name in ("one.md", "two.md"):
        (output_dir / name).write_text(name, encoding="utf-8")

    result = workflow_finalize(
        tmp_path,
        retention={
            "directory": ".evidraft/reviews",
            "pattern": "*.md",
            "keep_last": 1,
        },
    )

    assert len(result.removed) == 1
    assert len(list(output_dir.glob("*.md"))) == 1
    assert yaml.safe_load((tmp_path / ".evidraft/project.yaml").read_text())["format_version"] == 2


def test_cli_exposes_grouped_workflow_and_snapshot_commands(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(tmp_path, _project_doc(format_version=2))
    assert cli_main(["--root", str(tmp_path), "workflow", "preflight", "paper.lit"]) == 0
    assert json.loads(capsys.readouterr().out)["scope"] == "pass"
    evidence = append_evidence(tmp_path, _evidence_record())
    assert (
        cli_main(
            [
                "--root",
                str(tmp_path),
                "workflow",
                "preflight",
                "paper.lit",
                "--evidence-id",
                evidence["id"],
            ]
        )
        == 0
    )
    capsys.readouterr()
    with pytest.raises(PreflightError, match="write zone"):
        cli_main(
            [
                "--root",
                str(tmp_path),
                "workflow",
                "preflight",
                "xreview.run",
                "--target",
                "manuscript/main.tex",
            ]
        )
    assert (
        cli_main(
            [
                "--root",
                str(tmp_path),
                "workflow",
                "preflight",
                "xreview.run",
                "--read-target",
                "manuscript/main.tex",
                "--target",
                ".evidraft/reviews/report.md",
            ]
        )
        == 0
    )
    capsys.readouterr()

    source = tmp_path / "source.txt"
    source.write_bytes(b"source")
    assert (
        cli_main(
            [
                "--root",
                str(tmp_path),
                "snapshot",
                "store",
                "https://example.test/source",
                str(source),
            ]
        )
        == 0
    )
    stored = Path(capsys.readouterr().out.strip())
    assert stored.read_bytes() == b"source"

    reviews = tmp_path / ".evidraft" / "reviews"
    reviews.mkdir(parents=True)
    (reviews / "one.md").write_text("one", encoding="utf-8")
    (reviews / "two.md").write_text("two", encoding="utf-8")
    assert (
        cli_main(
            [
                "--root",
                str(tmp_path),
                "workflow",
                "finalize",
                "--directory",
                ".evidraft/reviews",
                "--pattern",
                "*.md",
                "--keep-last",
                "1",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["removed"]


def test_installed_package_runs_cli_outside_repository(tmp_path: Path) -> None:
    target = tmp_path / "site"
    install = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "--no-deps",
            "--no-build-isolation",
            "--target",
            str(target),
            str(REPO_ROOT),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert install.returncode == 0, install.stderr
    environment = {**os.environ, "PYTHONPATH": str(target)}
    smoke = subprocess.run(
        [sys.executable, "-m", "evidraft.cli", "--help"],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert smoke.returncode == 0, smoke.stderr
    for script in (
        "evidraft",
        "evidraft-claude-code",
        "evidraft-codex-cli",
        "evidraft-opencode",
    ):
        entrypoint_smoke = subprocess.run(
            [str(target / "bin" / script), "--help"],
            cwd=tmp_path,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert entrypoint_smoke.returncode == 0, (
            f"{script} failed outside repository:\n{entrypoint_smoke.stderr}"
        )
    installed_project = tmp_path / "installed-project"
    _write_project(installed_project)
    migrate = subprocess.run(
        [
            sys.executable,
            "-m",
            "evidraft.cli",
            "--root",
            str(installed_project),
            "migrate",
        ],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert migrate.returncode == 0, migrate.stderr
    assert yaml.safe_load(
        (installed_project / ".evidraft/project.yaml").read_text(encoding="utf-8")
    )["format_version"] == 2
    metadata = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import importlib.metadata as m; "
                "d=m.distribution('scholar-ip-copilot'); "
                "assert any(e.name=='evidraft' and e.value=='evidraft.cli:main' "
                "for e in d.entry_points)"
            ),
        ],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert metadata.returncode == 0, metadata.stderr


def test_packaged_schemas_match_canonical_schemas() -> None:
    for name in ("project.schema.json", "evidence.schema.json"):
        assert (REPO_ROOT / "src/evidraft/schemas" / name).read_bytes() == (
            REPO_ROOT / "packages/core/schemas" / name
        ).read_bytes()
