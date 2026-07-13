"""Deterministic storage, migration, and policy primitives for EviDraft v2."""

from __future__ import annotations

import fnmatch
import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Iterator, Mapping, Sequence

import jsonschema
import yaml

FORMAT_VERSION = 2
PUBLISH_OPERATIONS = frozenset({"paper.draft", "patent.claims", "polish.run"})
WARN_SCOPE_OPERATIONS = frozenset({"paper.idea", "patent.scout", "research.deep"})
_PROJECTLESS_NOTE_OPERATIONS = frozenset(
    {"research.reading-list", "research.explain"}
)
DEFAULT_SENSITIVE_PATTERNS = (
    ".env",
    "**/.env*",
    "secrets/",
    "credentials.json",
    "**/*.pem",
    "**/*.key",
    "**/id_rsa*",
)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SOURCE_SCHEMA_DIR = _REPO_ROOT / "packages" / "core" / "schemas"
_PACKAGED_SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
_WEB_SOURCE_KINDS = frozenset({"blog", "engineering_report", "docs", "tutorial", "spec"})
_SNAPSHOT_NAME = re.compile(r"^(?P<digest>[0-9a-f]{64})\.md$")
_MIGRATION_JOURNAL = ".migration-journal.json"


class MigrationError(RuntimeError):
    """Raised when a project cannot be migrated without risking data loss."""


class EvidenceError(RuntimeError):
    """Raised when the evidence store violates its integrity contract."""


class PreflightError(RuntimeError):
    """Raised when an executable policy blocks a workflow operation."""


@dataclass(frozen=True)
class MigrationResult:
    changed: bool
    source_version: int
    target_version: int
    backup_dir: Path | None = None
    quarantined: int = 0


@dataclass(frozen=True)
class PreflightResult:
    operation: str
    scope: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class FinalizeResult:
    removed: tuple[Path, ...] = ()


def detect_format_version(project: Mapping[str, object]) -> int:
    """Return the project data version; unversioned projects are v1."""
    value = project.get("format_version", 1)
    if isinstance(value, bool) or not isinstance(value, int) or value not in (1, 2):
        raise MigrationError(f"unsupported format_version: {value!r}")
    return value


def _load_schema(name: str) -> dict:
    for directory in (_PACKAGED_SCHEMA_DIR, _SOURCE_SCHEMA_DIR):
        path = directory / name
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"packaged schema does not exist: {name}")


def _validate(document: Mapping[str, object], schema_name: str, error_type: type[Exception]) -> None:
    try:
        jsonschema.Draft202012Validator(
            _load_schema(schema_name), format_checker=jsonschema.FormatChecker()
        ).validate(document)
    except jsonschema.ValidationError as exc:
        location = ".".join(str(part) for part in exc.absolute_path) or "<root>"
        raise error_type(f"schema validation failed at {location}: {exc.message}") from exc


@contextmanager
def _exclusive_lock(path: Path, *, wait: bool, timeout: float = 10.0) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    token = secrets.token_hex(16)
    payload = (
        json.dumps({"pid": os.getpid(), "token": token}, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()
    while True:
        if _publish_lock(path, payload):
            break
        owner, _, observed_raw = _read_lock_metadata(path)
        if owner is not None and not _pid_is_alive(owner) and observed_raw is not None:
            _release_owned_lock(path, observed_raw=observed_raw)
            continue
        if not wait or time.monotonic() >= deadline:
            raise MigrationError(f"migration or evidence store is locked: {path}")
        time.sleep(0.02)
    try:
        yield
    finally:
        _release_owned_lock(path, token=token)


@contextmanager
def _process_lock(path: Path, *, wait: bool, timeout: float = 10.0) -> Iterator[None]:
    """Hold an OS-released cross-process lock for a complete migration lifetime."""
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise MigrationError(f"cannot open migration process lock: {path}: {exc}") from exc
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if not wait or time.monotonic() >= deadline:
                    raise MigrationError("migration process lock is active") from exc
                time.sleep(0.02)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _publish_lock(path: Path, payload: bytes) -> bool:
    """Atomically publish a fully written owner record at ``path``."""
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp_path, path)
        except FileExistsError:
            return False
        return True
    finally:
        temp_path.unlink(missing_ok=True)


def _atomic_replace(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _validated_evidraft_dir(root: Path, error_type: type[Exception]) -> Path:
    evidraft = root / ".evidraft"
    if evidraft.is_symlink():
        raise error_type(f".evidraft must not be a symlink: {evidraft}")
    resolved = evidraft.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise error_type(f".evidraft escapes the project root: {evidraft}") from exc
    return evidraft


def _internal_path(
    root: Path,
    relative: Path | str,
    error_type: type[Exception],
) -> Path:
    evidraft = _validated_evidraft_dir(root, error_type)
    value = Path(relative)
    if value.is_absolute() or ".." in value.parts:
        raise error_type(f"internal path escapes the project root: {relative}")
    path = evidraft / value
    _reject_symlink_components(
        root,
        Path(".evidraft") / value,
        error_type,
        label="internal path",
    )
    try:
        path.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise error_type(f"internal path escapes the project root: {path}") from exc
    return path


def _reject_symlink_components(
    root: Path,
    value: Path | str,
    error_type: type[Exception],
    *,
    label: str,
) -> Path:
    candidate = Path(value)
    lexical = candidate if candidate.is_absolute() else root / candidate
    try:
        relative = lexical.relative_to(root)
    except ValueError as exc:
        raise error_type(f"{label} escapes the project root: {value}") from exc
    current = root
    for component in relative.parts:
        current /= component
        if current.is_symlink():
            raise error_type(f"{label} contains symlink component: {current}")
    return lexical


def _safe_transaction_path(base: Path, relative: object, *, label: str) -> Path:
    if not isinstance(relative, str):
        raise MigrationError(f"migration journal {label} must be a relative string")
    value = Path(relative)
    if value.is_absolute() or ".." in value.parts:
        raise MigrationError(f"migration journal {label} contains path traversal: {relative}")
    resolved = (base / value).resolve()
    try:
        resolved.relative_to(base.resolve())
    except ValueError as exc:
        raise MigrationError(f"migration journal {label} escapes .evidraft: {relative}") from exc
    return resolved


def _read_lock_metadata(lock_path: Path) -> tuple[int | None, str | None, bytes | None]:
    try:
        raw = lock_path.read_bytes()
    except OSError:
        return None, None, None
    try:
        metadata = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError):
        metadata = None
    if isinstance(metadata, dict):
        pid = metadata.get("pid")
        token = metadata.get("token")
        if isinstance(pid, int) and not isinstance(pid, bool) and isinstance(token, str):
            return pid, token, raw
    match = re.fullmatch(rb"pid=(\d+)\n?", raw)
    if match:
        return int(match.group(1)), None, raw
    return None, None, raw


def _lock_owner(lock_path: Path) -> int | None:
    owner, _, _ = _read_lock_metadata(lock_path)
    return owner


def _release_owned_lock(
    lock_path: Path,
    *,
    token: str | None = None,
    observed_raw: bytes | None = None,
) -> bool:
    _, current_token, current_raw = _read_lock_metadata(lock_path)
    if current_raw is None:
        return False
    owned = current_token == token if token is not None else current_raw == observed_raw
    if not owned:
        return False
    try:
        lock_path.unlink()
    except FileNotFoundError:
        return False
    return True


def _pid_is_alive(pid: int | None) -> bool:
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _load_migration_journal(journal_path: Path) -> dict:
    try:
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MigrationError(f"cannot read migration journal: {exc}") from exc
    if not isinstance(journal, dict) or journal.get("version") != 1:
        raise MigrationError("unsupported or malformed migration journal")
    if not isinstance(journal.get("entries"), list):
        raise MigrationError("migration journal entries must be a list")
    return journal


def _write_migration_journal(path: Path, journal: Mapping[str, object]) -> None:
    _atomic_replace(
        path,
        (json.dumps(journal, sort_keys=True, separators=(",", ":")) + "\n").encode(),
    )


def _recover_interrupted_migration(
    evidraft_dir: Path,
    *,
    wait: bool = False,
    force: bool = False,
    timeout: float = 10.0,
) -> bool:
    journal_path = evidraft_dir / _MIGRATION_JOURNAL
    lock_path = evidraft_dir / ".migration.lock"
    deadline = time.monotonic() + timeout
    observed_raw: bytes | None = None
    while lock_path.exists() and not force:
        owner, _, observed_raw = _read_lock_metadata(lock_path)
        if owner is not None and not _pid_is_alive(owner):
            break
        if not wait or time.monotonic() >= deadline:
            if owner is None:
                raise MigrationError("migration is locked: owner metadata is invalid")
            raise MigrationError(f"migration transaction is active under pid {owner}")
        time.sleep(0.02)
    if not journal_path.exists():
        if lock_path.exists() and observed_raw is not None:
            _release_owned_lock(lock_path, observed_raw=observed_raw)
        return False

    journal = _load_migration_journal(journal_path)
    backup_dir = _safe_transaction_path(
        evidraft_dir, journal.get("backup_dir"), label="backup_dir"
    )
    backups_root = (evidraft_dir / "backups").resolve()
    try:
        backup_dir.relative_to(backups_root)
    except ValueError as exc:
        raise MigrationError("migration journal backup_dir is outside backups/") from exc

    entries = journal["entries"]
    for entry in reversed(entries):
        if not isinstance(entry, dict):
            raise MigrationError("migration journal entry must be an object")
        if entry.get("replaced") is not True:
            continue
        target = _safe_transaction_path(
            evidraft_dir, entry.get("path"), label="entry.path"
        )
        existed = entry.get("existed")
        if not isinstance(existed, bool):
            raise MigrationError("migration journal entry.existed must be boolean")
        if existed:
            backup = _safe_transaction_path(
                backup_dir, entry.get("path"), label="backup entry.path"
            )
            if not backup.is_file():
                raise MigrationError(f"migration backup is missing: {backup}")
            _atomic_replace(target, backup.read_bytes())
        else:
            if target.is_dir() and not target.is_symlink():
                raise MigrationError(f"refusing to remove migration directory target: {target}")
            target.unlink(missing_ok=True)
    journal_path.unlink()
    if not force and observed_raw is not None:
        _release_owned_lock(lock_path, observed_raw=observed_raw)
    return True


def _load_project(project_path: Path) -> dict:
    try:
        document = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise MigrationError(f"cannot read project descriptor {project_path}: {exc}") from exc
    if not isinstance(document, dict):
        raise MigrationError(f"project descriptor must be a YAML mapping: {project_path}")
    return document


def _relative_to_evidraft(path: Path, evidraft_dir: Path) -> Path:
    try:
        return path.relative_to(evidraft_dir)
    except ValueError as exc:
        raise MigrationError(f"migration target escapes .evidraft: {path}") from exc


def _snapshot_destination(raw: bytes) -> Path:
    digest = hashlib.sha256(raw).hexdigest()
    return Path(".evidraft") / "literature" / "snapshots" / f"{digest}.md"


def _assert_existing_snapshot_matches(path: Path, expected: bytes) -> None:
    if not path.exists():
        return
    actual = path.read_bytes()
    expected_digest = hashlib.sha256(expected).hexdigest()
    actual_digest = hashlib.sha256(actual).hexdigest()
    if actual != expected or actual_digest != expected_digest:
        raise MigrationError(
            f"snapshot content hash mismatch or corrupt destination: {path}"
        )


def _graph_invalid_indexes(candidates: Sequence[tuple[dict, str]]) -> set[int]:
    invalid: set[int] = set()
    seen_ids: set[str] = set()
    for index, (record, _) in enumerate(candidates):
        identifier = record["id"]
        if identifier in seen_ids:
            invalid.add(index)
        else:
            seen_ids.add(identifier)

    while True:
        before = set(invalid)
        active = [index for index in range(len(candidates)) if index not in invalid]
        by_id = {candidates[index][0]["id"]: index for index in active}

        successors: dict[str, list[int]] = {}
        for index in active:
            previous = candidates[index][0].get("supersedes")
            if previous is None:
                continue
            if previous not in by_id:
                invalid.add(index)
                continue
            successors.setdefault(previous, []).append(index)
        for indexes in successors.values():
            invalid.update(indexes[1:])

        active = [index for index in range(len(candidates)) if index not in invalid]
        by_id = {candidates[index][0]["id"]: index for index in active}
        for start in list(by_id):
            order: list[str] = []
            positions: dict[str, int] = {}
            current: str | None = start
            while current is not None and current in by_id:
                if current in positions:
                    invalid.update(by_id[item] for item in order[positions[current] :])
                    break
                positions[current] = len(order)
                order.append(current)
                current = candidates[by_id[current]][0].get("supersedes")
        if invalid == before:
            return invalid


def _prepare_evidence_migration(
    root: Path, evidence_path: Path
) -> tuple[bytes, bytes, dict[Path, bytes], int]:
    candidates: list[tuple[dict, str]] = []
    quarantine_parts: list[str] = []
    snapshots: dict[Path, bytes] = {}
    if not evidence_path.exists():
        return b"", b"", snapshots, 0

    for raw_line in evidence_path.read_text(encoding="utf-8").splitlines(keepends=True):
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line)
            if not isinstance(record, dict):
                raise ValueError("record is not an object")
            file_path = record.get("file_path")
            if record.get("source_kind") in _WEB_SOURCE_KINDS and isinstance(file_path, str):
                source_path = (root / file_path).resolve()
                source_path.relative_to(root.resolve())
                if not source_path.is_file():
                    raise ValueError(f"snapshot does not exist: {file_path}")
                body = source_path.read_bytes()
                destination = _snapshot_destination(body)
                destination_path = _internal_path(
                    root,
                    destination.relative_to(".evidraft"),
                    MigrationError,
                )
                _assert_existing_snapshot_matches(destination_path, body)
                snapshots[destination_path] = body
                record["file_path"] = destination.as_posix()
            _validate(record, "evidence.schema.json", EvidenceError)
            if record.get("source_kind") not in _WEB_SOURCE_KINDS:
                _validate_record_storage(root, record)
        except (EvidenceError, OSError, ValueError, json.JSONDecodeError):
            quarantine_parts.append(raw_line if raw_line.endswith("\n") else raw_line + "\n")
            continue
        candidates.append((record, raw_line if raw_line.endswith("\n") else raw_line + "\n"))

    graph_invalid = _graph_invalid_indexes(candidates)
    quarantine_parts.extend(candidates[index][1] for index in sorted(graph_invalid))
    kept = [record for index, (record, _) in enumerate(candidates) if index not in graph_invalid]
    valid_lines = [
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n" for record in kept
    ]
    referenced_snapshots = {
        (root / record["file_path"]).resolve()
        for record in kept
        if record.get("source_kind") in _WEB_SOURCE_KINDS
        and isinstance(record.get("file_path"), str)
    }
    snapshots = {path: body for path, body in snapshots.items() if path in referenced_snapshots}
    return (
        "".join(valid_lines).encode(),
        "".join(quarantine_parts).encode(),
        snapshots,
        len(quarantine_parts),
    )


def migrate_project(root: Path | str, *, wait_for_lock: bool = False) -> MigrationResult:
    """Transactionally migrate an unversioned/v1 project to format v2."""
    root = Path(root).resolve()
    evidraft_dir = _validated_evidraft_dir(root, MigrationError)
    guard_path = _internal_path(root, ".migration.guard", MigrationError)
    with _process_lock(guard_path, wait=wait_for_lock):
        return _migrate_project_locked(root, evidraft_dir, wait_for_lock=wait_for_lock)


def _migrate_project_locked(
    root: Path,
    evidraft_dir: Path,
    *,
    wait_for_lock: bool,
) -> MigrationResult:
    project_path = _internal_path(root, "project.yaml", MigrationError)
    _recover_interrupted_migration(evidraft_dir, wait=wait_for_lock)
    if not project_path.is_file():
        raise MigrationError(f"project descriptor does not exist: {project_path}")

    initial = _load_project(project_path)
    source_version = detect_format_version(initial)
    if source_version == FORMAT_VERSION:
        return MigrationResult(False, FORMAT_VERSION, FORMAT_VERSION)

    lock_path = _internal_path(root, ".migration.lock", MigrationError)
    with _exclusive_lock(lock_path, wait=wait_for_lock):
        current = _load_project(project_path)
        current_version = detect_format_version(current)
        if current_version == FORMAT_VERSION:
            return MigrationResult(False, FORMAT_VERSION, FORMAT_VERSION)

        migrated = dict(current)
        migrated["format_version"] = FORMAT_VERSION
        _validate(migrated, "project.schema.json", MigrationError)
        if migrated.get("format_version") != FORMAT_VERSION:
            raise MigrationError("schema validation did not produce a v2 project")

        evidence_path = _internal_path(root, "evidence/evidence.jsonl", MigrationError)
        quarantine_path = _internal_path(root, "evidence/quarantine.jsonl", MigrationError)
        evidence_body, new_quarantine, snapshots, quarantined = _prepare_evidence_migration(
            root, evidence_path
        )
        if evidence_body:
            migrated_records = [
                json.loads(line) for line in evidence_body.decode().splitlines() if line.strip()
            ]
            try:
                _index_evidence(migrated_records)
            except EvidenceError as exc:
                raise MigrationError(f"evidence integrity validation failed: {exc}") from exc
        old_quarantine = quarantine_path.read_bytes() if quarantine_path.exists() else b""
        outputs: dict[Path, bytes] = {
            project_path: yaml.safe_dump(migrated, sort_keys=False, allow_unicode=True).encode(),
        }
        if evidence_path.exists():
            outputs[evidence_path] = evidence_body
        if new_quarantine or quarantine_path.exists():
            outputs[quarantine_path] = old_quarantine + new_quarantine
        for snapshot_path, body in snapshots.items():
            if not snapshot_path.exists():
                outputs[snapshot_path] = body

        required_bytes = sum(len(body) for body in outputs.values()) * 2
        if shutil.disk_usage(root).free < required_bytes:
            raise MigrationError(
                f"insufficient disk space for migration: need {required_bytes} bytes"
            )

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        backup_dir = _internal_path(
            root,
            f"backups/v1-to-v2-{stamp}-{os.getpid()}",
            MigrationError,
        )
        originals: dict[Path, bytes | None] = {}
        for path in outputs:
            originals[path] = path.read_bytes() if path.exists() else None
        for path, original in originals.items():
            if original is None:
                continue
            backup_path = backup_dir / _relative_to_evidraft(path, evidraft_dir)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_bytes(original)

        ordered = [path for path in outputs if path != project_path] + [project_path]
        journal_path = _internal_path(root, _MIGRATION_JOURNAL, MigrationError)
        journal: dict[str, object] = {
            "version": 1,
            "backup_dir": backup_dir.relative_to(evidraft_dir).as_posix(),
            "entries": [
                {
                    "path": path.relative_to(evidraft_dir).as_posix(),
                    "existed": originals[path] is not None,
                    "replaced": False,
                }
                for path in ordered
            ],
        }
        _write_migration_journal(journal_path, journal)
        try:
            # The project descriptor is the commit marker and is replaced last.
            entries = journal["entries"]
            assert isinstance(entries, list)
            for index, path in enumerate(ordered):
                entry = entries[index]
                assert isinstance(entry, dict)
                # Mark before replacement so recovery is conservative across a hard kill
                # in the small window between os.replace and the next journal write.
                entry["replaced"] = True
                _write_migration_journal(journal_path, journal)
                _atomic_replace(path, outputs[path])
        except BaseException as exc:
            _recover_interrupted_migration(evidraft_dir, force=True)
            if isinstance(exc, (KeyboardInterrupt, SystemExit, GeneratorExit)):
                raise
            raise MigrationError(f"migration failed and was rolled back: {exc}") from exc
        # Commit is complete once every replacement succeeds. Remove the journal;
        # the lock remains owned until the context exits and token-checks release.
        journal_path.unlink()

        return MigrationResult(
            True,
            source_version,
            FORMAT_VERSION,
            backup_dir=backup_dir,
            quarantined=quarantined,
        )


def _ensure_v2(root: Path) -> None:
    _validated_evidraft_dir(root, EvidenceError)
    # Always enter the process guard: a hard-killed migration may have written
    # the v2 commit marker while its recovery journal still requires rollback.
    migrate_project(root, wait_for_lock=True)


def _read_evidence(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvidenceError(f"invalid JSON on evidence line {line_number}: {exc.msg}") from exc
        if not isinstance(record, dict):
            raise EvidenceError(f"evidence line {line_number} is not an object")
        _validate(record, "evidence.schema.json", EvidenceError)
        records.append(record)
    return records


def append_evidence(root: Path | str, record: Mapping[str, object]) -> dict:
    """Validate and append one record while allocating a process-safe stable ID."""
    root = Path(root).resolve()
    _ensure_v2(root)
    if "id" in record:
        raise EvidenceError("evidence append allocates id; callers must not provide one")
    evidence_dir = _internal_path(root, "evidence", EvidenceError)
    evidence_path = _internal_path(root, "evidence/evidence.jsonl", EvidenceError)
    try:
        with _process_lock(evidence_dir / ".append.lock", wait=True):
            records = _read_evidence(evidence_path)
            ids, superseded_by = _index_evidence(records)
            supersedes = record.get("supersedes")
            if supersedes is not None and supersedes not in ids:
                raise EvidenceError(f"supersedes target does not exist: {supersedes}")
            if supersedes is not None and supersedes in superseded_by:
                raise EvidenceError(
                    f"evidence is already superseded: {supersedes} by {superseded_by[supersedes]}"
                )
            highest = max((int(item["id"].split("_", 1)[1]) for item in records), default=0)
            result = dict(record)
            result["id"] = f"ev_{highest + 1:04d}"
            _validate(result, "evidence.schema.json", EvidenceError)
            _validate_record_storage(root, result)
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            with evidence_path.open("ab") as handle:
                handle.write((json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode())
                handle.flush()
                os.fsync(handle.fileno())
            return result
    except MigrationError as exc:
        raise EvidenceError(str(exc)) from exc


def _index_evidence(records: Sequence[dict]) -> tuple[dict[str, dict], dict[str, str]]:
    by_id: dict[str, dict] = {}
    superseded_by: dict[str, str] = {}
    for record in records:
        identifier = record["id"]
        if identifier in by_id:
            raise EvidenceError(f"duplicate evidence id: {identifier}")
        by_id[identifier] = record
    for record in records:
        previous = record.get("supersedes")
        if previous is None:
            continue
        if previous not in by_id:
            raise EvidenceError(f"supersedes target does not exist: {previous}")
        if previous in superseded_by:
            raise EvidenceError(f"ambiguous supersedes chain for {previous}")
        superseded_by[previous] = record["id"]

    for start in by_id:
        seen: set[str] = set()
        current: str | None = start
        while current is not None:
            if current in seen:
                raise EvidenceError(f"supersedes cycle detected at {current}")
            seen.add(current)
            current = by_id[current].get("supersedes")
    return by_id, superseded_by


def _validate_record_storage(root: Path, record: Mapping[str, object]) -> None:
    record_type = record.get("type")
    is_web = record.get("source_kind") in _WEB_SOURCE_KINDS
    if not is_web and record_type not in {"code", "experiment"}:
        return
    file_path = record.get("file_path")
    if not isinstance(file_path, str):
        raise EvidenceError(f"{record_type} evidence file_path is required")
    relative = Path(file_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise EvidenceError("evidence file_path must be project-relative without traversal")
    resolved_file = _reject_symlink_components(
        root,
        file_path,
        EvidenceError,
        label="evidence file_path",
    )
    if is_sensitive_path(relative):
        raise EvidenceError(f"evidence file_path is sensitive: {file_path}")
    if not resolved_file.is_file():
        label = "web evidence snapshot" if is_web else f"{record_type} evidence file_path"
        raise EvidenceError(f"{label} does not exist: {file_path}")
    if not is_web:
        line_range = record.get("line_range")
        if not isinstance(line_range, str):
            raise EvidenceError(f"{record_type} evidence line_range is required")
        start, end = (int(value) for value in line_range.split(":"))
        line_count = len(resolved_file.read_bytes().splitlines())
        if start < 1 or end < start or end > line_count:
            raise EvidenceError(
                f"evidence line_range is out of bounds for {file_path}: {line_range}"
            )
        return

    snapshots_root = root / ".evidraft" / "literature" / "snapshots"
    snapshot = resolved_file
    try:
        snapshot.relative_to(snapshots_root)
    except ValueError as exc:
        raise EvidenceError("web evidence snapshot must be in the snapshot store") from exc
    match = _SNAPSHOT_NAME.fullmatch(snapshot.name)
    if match is None:
        raise EvidenceError("web evidence snapshot must use a SHA-256 content-addressed name")
    actual_digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    if actual_digest != match.group("digest"):
        raise EvidenceError(f"web evidence snapshot hash mismatch: {file_path}")


def resolve_evidence(
    root: Path | str, identifier: str, *, follow_supersedes: bool = True
) -> dict:
    """Resolve a stable evidence ID to a verified current record."""
    root = Path(root).resolve()
    _validated_evidraft_dir(root, EvidenceError)
    evidence_path = _internal_path(root, "evidence/evidence.jsonl", EvidenceError)
    records = _read_evidence(evidence_path)
    by_id, superseded_by = _index_evidence(records)
    if identifier not in by_id:
        raise EvidenceError(f"evidence does not exist: {identifier}")
    current = identifier
    if follow_supersedes:
        while current in superseded_by:
            current = superseded_by[current]
    record = by_id[current]
    _validate_record_storage(root, record)
    if record.get("verified") is not True:
        raise EvidenceError(f"evidence is not verified: {current}")
    return dict(record)


def store_snapshot(root: Path | str, url: str, raw: bytes) -> Path:
    """Store immutable raw content under its SHA-256 digest."""
    if not isinstance(raw, bytes):
        raise TypeError("raw snapshot content must be bytes")
    if not isinstance(url, str) or not url.strip():
        raise ValueError("snapshot URL must be a non-empty string")
    root = Path(root).resolve()
    _ensure_v2(root)
    destination = _snapshot_destination(raw).relative_to(".evidraft")
    path = _internal_path(root, destination, EvidenceError)
    if path.exists():
        if path.read_bytes() != raw:
            raise EvidenceError(f"snapshot hash collision or corruption: {path}")
        return path
    _atomic_replace(path, raw)
    return path


def scope_policy(operation: str) -> str:
    if operation in PUBLISH_OPERATIONS:
        return "block"
    if operation in WARN_SCOPE_OPERATIONS:
        return "warn"
    return "pass"


def is_sensitive_path(
    path: Path | str, forbidden_patterns: Sequence[str] = DEFAULT_SENSITIVE_PATTERNS
) -> bool:
    value = str(path).replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    pure = PurePosixPath(value)
    name = pure.name
    parts = pure.parts
    built_in = (
        name == ".env"
        or name.startswith(".env.")
        or "secrets" in parts
        or name == "credentials.json"
        or name.endswith((".pem", ".key"))
        or name.startswith("id_rsa")
    )
    if built_in:
        return True
    candidates = (value, f"./{value}")
    for pattern in forbidden_patterns:
        normalized = pattern.rstrip("/")
        if any(fnmatch.fnmatch(candidate, normalized) for candidate in candidates):
            return True
        if pattern.endswith("/") and normalized in parts:
            return True
    return False


def _resolve_within(root: Path, value: Path | str, *, label: str) -> Path:
    candidate = Path(value)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PreflightError(f"{label} escapes the project root: {value}") from exc
    return resolved


def _has_quarantine(root: Path) -> bool:
    path = _internal_path(root, "evidence/quarantine.jsonl", PreflightError)
    return path.exists() and bool(path.read_text(encoding="utf-8").strip())


def _validate_preflight_evidence(root: Path, evidence_ids: Sequence[str]) -> None:
    path = _internal_path(root, "evidence/evidence.jsonl", PreflightError)
    try:
        records = _read_evidence(path)
        by_id, superseded_by = _index_evidence(records)
        for identifier, record in by_id.items():
            if identifier not in superseded_by:
                _validate_record_storage(root, record)
        for identifier in evidence_ids:
            if identifier not in by_id:
                raise EvidenceError(f"required evidence does not exist: {identifier}")
            if identifier in superseded_by:
                raise EvidenceError(
                    f"required evidence is superseded: {identifier} by {superseded_by[identifier]}"
                )
            if by_id[identifier].get("verified") is not True:
                raise EvidenceError(f"required evidence is not verified: {identifier}")
    except EvidenceError as exc:
        raise PreflightError(f"evidence-integrity: {exc}") from exc


def workflow_preflight(
    root: Path | str,
    operation: str,
    *,
    read_paths: Sequence[Path | str] = (),
    target_paths: Sequence[Path | str] = (),
    write_zone: Path | str | None = None,
    evidence_ids: Sequence[str] = (),
    today: date | None = None,
) -> PreflightResult:
    """Enforce executable workspace, scope, and evidence-integrity policies."""
    root = Path(root).resolve()
    project_path = _internal_path(root, "project.yaml", PreflightError)
    project: Mapping[str, object] = {}
    if project_path.is_file() or operation not in _PROJECTLESS_NOTE_OPERATIONS:
        try:
            _ensure_v2(root)
        except (EvidenceError, MigrationError) as exc:
            raise PreflightError(f"project migration failed before preflight: {exc}") from exc
        project = _load_project(project_path)
    safety = project.get("safety", {})
    custom_patterns = safety.get("forbidden_paths", []) if isinstance(safety, dict) else []
    if not isinstance(custom_patterns, list) or not all(
        isinstance(pattern, str) for pattern in custom_patterns
    ):
        custom_patterns = []
    forbidden_patterns = (*DEFAULT_SENSITIVE_PATTERNS, *custom_patterns)
    for read_path in read_paths:
        _reject_symlink_components(
            root,
            read_path,
            PreflightError,
            label="read path",
        )
    if operation == "xreview.run":
        if not target_paths:
            raise PreflightError("xreview.run target path is required for write zone enforcement")
        _reject_symlink_components(
            root,
            ".evidraft/reviews",
            PreflightError,
            label="xreview.run write zone",
        )
        for target in target_paths:
            _reject_symlink_components(
                root,
                target,
                PreflightError,
                label="xreview.run target path",
            )
        canonical_zone = _resolve_within(root, ".evidraft/reviews", label="write zone")
        if write_zone is not None:
            requested_zone = _resolve_within(root, write_zone, label="write zone")
            if requested_zone != canonical_zone:
                raise PreflightError("xreview.run write zone is fixed to .evidraft/reviews")
        write_zone = ".evidraft/reviews"
    resolved_targets = [
        _resolve_within(root, path, label="target path") for path in target_paths
    ]
    resolved_reads = [_resolve_within(root, path, label="read path") for path in read_paths]
    unsafe = [
        str(path.relative_to(root))
        for path in (*resolved_reads, *resolved_targets)
        if is_sensitive_path(path.relative_to(root), forbidden_patterns)
    ]
    if unsafe:
        raise PreflightError(f"sensitive workspace path blocked: {', '.join(unsafe)}")
    if write_zone is not None:
        zone = _resolve_within(root, write_zone, label="write zone")
        violations: list[str] = []
        for target in resolved_targets:
            try:
                target.relative_to(zone)
            except ValueError:
                violations.append(str(target.relative_to(root)))
        if violations:
            raise PreflightError(
                f"external write zone violation ({write_zone}): {', '.join(violations)}"
            )
    if operation in PUBLISH_OPERATIONS and _has_quarantine(root):
        raise PreflightError("publish operation blocked: evidence quarantine is not empty")
    _validate_preflight_evidence(root, evidence_ids)

    policy = scope_policy(operation)
    warnings: list[str] = []
    if policy == "pass":
        return PreflightResult(operation=operation, scope=policy)
    reason = _scope_failure_reason(root, project, today=today or date.today())
    if policy == "block" and reason is not None:
        raise PreflightError(f"scope is required for {operation}: {reason}")
    if policy == "warn" and reason is not None:
        warnings.append(f"scope is {reason} for {operation}")
    return PreflightResult(operation=operation, scope=policy, warnings=tuple(warnings))


def _latest_scope_file(scope_dir: Path) -> Path | None:
    files = list(scope_dir.glob("*.md")) if scope_dir.is_dir() else []
    if not files:
        return None
    dated = [path for path in files if re.match(r"^\d{4}-\d{2}-\d{2}-", path.name)]
    if dated:
        return max(dated, key=lambda path: (path.name[:10], path.stat().st_mtime_ns, path.name))
    return max(files, key=lambda path: (path.stat().st_mtime_ns, path.name))


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return {}
    try:
        document = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError:
        return {}
    return document if isinstance(document, dict) else {}


def _scope_failure_reason(root: Path, project: Mapping[str, object], *, today: date) -> str | None:
    scope_dir = _internal_path(root, "scope", PreflightError)
    _reject_symlink_components(
        root,
        scope_dir,
        PreflightError,
        label="scope directory",
    )
    latest = _latest_scope_file(scope_dir)
    if latest is None:
        return "missing"
    _reject_symlink_components(
        root,
        latest,
        PreflightError,
        label="scope file",
    )
    metadata = _frontmatter(latest)
    if metadata.get("status") != "approved":
        return "draft-only"
    approved_value = metadata.get("approved_date")
    if isinstance(approved_value, datetime):
        approved = approved_value.date()
    elif isinstance(approved_value, date):
        approved = approved_value
    elif isinstance(approved_value, str):
        try:
            approved = date.fromisoformat(approved_value)
        except ValueError:
            return "stale"
    else:
        return "stale"
    scope_config = project.get("scope", {})
    staleness_days = scope_config.get("staleness_days", 14) if isinstance(scope_config, dict) else 14
    if isinstance(staleness_days, bool) or not isinstance(staleness_days, int):
        staleness_days = 14
    if approved > today or today - approved > timedelta(days=staleness_days):
        return "stale"
    return None


def prune_retention(
    directory: Path | str,
    *,
    pattern: str = "*",
    keep_last: int | None = None,
    max_age_days: int | None = None,
    now: datetime | None = None,
) -> tuple[Path, ...]:
    """Prune regular files by age, then retain only the newest requested count."""
    if keep_last is not None and keep_last < 1:
        raise ValueError("keep_last must be at least 1")
    if max_age_days is not None and max_age_days < 1:
        raise ValueError("max_age_days must be at least 1")
    pattern_path = PurePosixPath(pattern.replace("\\", "/"))
    if pattern_path.is_absolute() or ".." in pattern_path.parts:
        raise ValueError("retention pattern traversal is not allowed")
    directory = Path(directory).resolve()
    if not directory.exists():
        return ()
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    files: list[Path] = []
    for path in directory.glob(pattern):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            path.resolve().relative_to(directory)
        except ValueError:
            continue
        files.append(path)
    files.sort(key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
    removed: list[Path] = []
    survivors: list[Path] = []
    for path in files:
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        expired = max_age_days is not None and current - modified > timedelta(days=max_age_days)
        if expired:
            path.unlink()
            removed.append(path)
        else:
            survivors.append(path)
    if keep_last is not None:
        for path in survivors[keep_last:]:
            path.unlink()
            removed.append(path)
    return tuple(removed)


def workflow_finalize(
    root: Path | str, *, retention: Mapping[str, object] | None = None
) -> FinalizeResult:
    """Apply deterministic post-run retention declared by a workflow action."""
    if not retention:
        return FinalizeResult()
    root = Path(root).resolve()
    directory_value = retention.get("directory")
    if not isinstance(directory_value, str):
        raise ValueError("retention.directory must be a project-relative string")
    relative_directory = Path(directory_value)
    if relative_directory.is_absolute() or ".." in relative_directory.parts:
        raise ValueError("retention.directory must be relative without traversal")
    directory = (root / relative_directory).resolve()
    try:
        directory.relative_to(root)
    except ValueError as exc:
        raise ValueError("retention.directory escapes the project root") from exc
    _ensure_v2(root)
    removed = prune_retention(
        directory,
        pattern=str(retention.get("pattern", "*")),
        keep_last=retention.get("keep_last") if isinstance(retention.get("keep_last"), int) else None,
        max_age_days=retention.get("max_age_days") if isinstance(retention.get("max_age_days"), int) else None,
    )
    return FinalizeResult(removed=removed)
