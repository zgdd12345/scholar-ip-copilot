from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable

import pytest

import evidraft.codex_install as codex_install
from evidraft.codex_install import reinstall_codex_plugin, validate_marketplace_plugin
from evidraft.install import PUBLIC_CODEX_SKILLS


MARKETPLACE_HEADER = "MARKETPLACE  ROOT\n"
PLUGIN_HEADER = "PLUGIN  STATUS  VERSION  PATH\n"


@pytest.fixture(autouse=True)
def _isolated_codex_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex-home"))
    monkeypatch.setattr(codex_install, "release_package_drift", lambda _source, _package: [])


def _build_release(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    repo = tmp_path / "repo"
    release = repo / "plugins" / "scholar"
    manifest = release / ".codex-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps({"name": "scholar", "version": "3.0.0"}, indent=2) + "\n",
        encoding="utf-8",
    )
    for name in (
        "using",
        "scope",
        "research",
        "paper",
        "patent",
        "polish",
        "xreview",
    ):
        skill = release / "skills" / f"scholar-{name}" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(f"# {name}\n", encoding="utf-8")
    marketplace = repo / ".agents" / "plugins" / "marketplace.json"
    marketplace.parent.mkdir(parents=True)
    marketplace.write_text(
        json.dumps(
            {
                "name": "scholar-ip-copilot",
                "plugins": [
                    {
                        "name": "scholar",
                        "source": {
                            "source": "local",
                            "path": "./plugins/scholar",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    creator = tmp_path / "plugin-creator"
    (creator / "scripts").mkdir(parents=True)
    for script in (
        "validate_plugin.py",
        "read_marketplace_name.py",
        "update_plugin_cachebuster.py",
    ):
        (creator / "scripts" / script).write_text("# fake helper\n", encoding="utf-8")
    return repo, marketplace, release, creator


def _seed_compatibility_state(repo: Path) -> tuple[Path, dict[str, bytes]]:
    destination = repo / ".agents" / "skills"
    files = {
        "scholar-paper/SKILL.md": b"# prior paper skill\n",
        "scholar-paper/references/state.bin": b"\x00prior\xff",
        ".evidraft-private/plugin.yaml": b"version: prior\n",
    }
    for relative, content in files.items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    manifest = destination / ".evidraft-ownership.json"
    manifest.write_bytes(
        b'{\n  "version": 2,\n  "owned_paths": ["scholar-paper"],'
        b'\n  "private_path": ".evidraft-private"\n}\n'
    )
    user = destination / "scholar-custom" / "SKILL.md"
    user.parent.mkdir(parents=True)
    user.write_bytes(b"# user skill\n")
    return destination, _compatibility_state(destination)


def _compatibility_state(destination: Path) -> dict[str, bytes]:
    return {
        path.relative_to(destination).as_posix(): path.read_bytes()
        for path in sorted(destination.rglob("*"))
        if path.is_file()
    }


def _is_manifest_restore_temporary(path: Path, manifest: Path) -> bool:
    return (
        path.parent == manifest.parent
        and path.name.startswith(f".{manifest.name}.restore-")
        and path != manifest
    )


def _plugin_list(version: str, path: Path, *, status: str = "installed, enabled") -> str:
    return (
        PLUGIN_HEADER
        + f"scholar@scholar-ip-copilot  {status}  {version}  {path.resolve()}\n"
    )


def _runner(
    release: Path,
    calls: list[list[str]],
    *,
    failing_step: str | None = None,
    marketplace_list: str | None = None,
    plugin_list_output: str | None = None,
    installed_skills: set[str] | None = None,
    operation_error: BaseException | None = None,
    expect_compatibility_removed: bool = False,
    cachebuster_action: Callable[[Path], None] | None = None,
) -> Callable[..., subprocess.CompletedProcess[str]]:
    marketplace_added = False

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal marketplace_added
        assert kwargs == {
            "cwd": release.parents[1].resolve(),
            "check": True,
            "capture_output": True,
            "text": True,
        }
        calls.append(command)
        compatibility = release.parents[1] / ".agents" / "skills"

        def assert_compatibility_removed() -> None:
            if expect_compatibility_removed:
                assert not (compatibility / ".evidraft-ownership.json").exists()
                assert not (compatibility / "scholar-paper").exists()
                assert not (compatibility / ".evidraft-private").exists()

        if command[1].endswith("validate_plugin.py") and failing_step == "source-validator":
            raise operation_error or RuntimeError("source-validator")
        if command[1].endswith("read_marketplace_name.py"):
            return subprocess.CompletedProcess(command, 0, "scholar-ip-copilot\n", "")
        if command[1].endswith("update_plugin_cachebuster.py"):
            assert_compatibility_removed()
            manifest = release / ".codex-plugin" / "plugin.json"
            if cachebuster_action is None:
                document = json.loads(manifest.read_text(encoding="utf-8"))
                document["version"] = "3.0.0+codex.test"
                manifest.write_text(json.dumps(document) + "\n", encoding="utf-8")
            else:
                cachebuster_action(manifest)
            if failing_step == "cachebuster":
                raise operation_error or RuntimeError("cachebuster")
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[-3:] == ["plugin", "marketplace", "list"]:
            output = marketplace_list or (
                MARKETPLACE_HEADER
                + f"scholar-ip-copilot  {release.parents[1].resolve()}\n"
            )
            if marketplace_added and "scholar-ip-copilot" not in output:
                output += f"scholar-ip-copilot  {release.parents[1].resolve()}\n"
            return subprocess.CompletedProcess(command, 0, output, "")
        if command[-4:-1] == ["plugin", "marketplace", "add"]:
            assert_compatibility_removed()
            if failing_step == "marketplace-add":
                raise operation_error or RuntimeError("marketplace-add")
            marketplace_added = True
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[-3:-1] == ["plugin", "add"]:
            assert_compatibility_removed()
            if failing_step == "plugin-add":
                raise operation_error or RuntimeError("plugin-add")
            manifest = release / ".codex-plugin" / "plugin.json"
            version = json.loads(manifest.read_text(encoding="utf-8"))["version"]
            cache = (
                Path(os.environ["CODEX_HOME"])
                / "plugins/cache/scholar-ip-copilot/scholar"
                / version
            )
            cached_manifest = cache / ".codex-plugin" / "plugin.json"
            cached_manifest.parent.mkdir(parents=True, exist_ok=True)
            cached_manifest.write_bytes(manifest.read_bytes())
            for name in PUBLIC_CODEX_SKILLS if installed_skills is None else installed_skills:
                skill = cache / "skills" / name / "SKILL.md"
                skill.parent.mkdir(parents=True, exist_ok=True)
                skill.write_text(f"# {name}\n", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[-2:] == ["plugin", "list"]:
            assert_compatibility_removed()
            if failing_step == "post-validate":
                if operation_error is not None:
                    raise operation_error
                return subprocess.CompletedProcess(
                    command,
                    0,
                    "scholar@scholar-ip-copilot installed, disabled\n",
                    "",
                )
            return subprocess.CompletedProcess(
                command,
                0,
                plugin_list_output
                or (
                    PLUGIN_HEADER
                    + "scholar@scholar-ip-copilot  installed, enabled  "
                    + json.loads(
                        (release / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
                    )["version"]
                    + f"  {release.resolve()}\n"
                ),
                "",
            )
        return subprocess.CompletedProcess(command, 0, "", "")

    return run


def test_reinstall_restores_base_manifest_after_success(tmp_path: Path) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    calls: list[list[str]] = []
    original = (release / ".codex-plugin" / "plugin.json").read_bytes()

    result = reinstall_codex_plugin(
        repo,
        marketplace,
        release,
        creator,
        runner=_runner(release, calls),
    )

    assert result.plugin_ref == "scholar@scholar-ip-copilot"
    assert result.installed_version == "3.0.0+codex.test"
    assert (release / ".codex-plugin" / "plugin.json").read_bytes() == original
    assert any(command[-3:] == ["plugin", "add", result.plugin_ref] for command in calls)
    cachebusters = [command for command in calls if command[1].endswith("update_plugin_cachebuster.py")]
    assert len(cachebusters) == 1
    assert calls[0][1].endswith("validate_plugin.py")
    assert calls[1][1].endswith("read_marketplace_name.py")
    assert calls[2][-3:] == ["plugin", "marketplace", "list"]
    assert calls[3][1].endswith("update_plugin_cachebuster.py")
    assert calls[4][-3:] == ["plugin", "add", result.plugin_ref]
    assert calls[5][-2:] == ["plugin", "list"]


def test_reinstall_rejects_same_name_marketplace_with_wrong_root_before_mutation(
    tmp_path: Path,
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    calls: list[list[str]] = []

    with pytest.raises(ValueError, match="marketplace root"):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(
                release,
                calls,
                marketplace_list=(
                    MARKETPLACE_HEADER
                    + f"scholar-ip-copilot  {tmp_path / 'different-repo'}\n"
                ),
            ),
        )

    assert all(
        not command[1].endswith("update_plugin_cachebuster.py")
        and command[-4:-1] != ["plugin", "marketplace", "add"]
        and command[-3:-1] != ["plugin", "add"]
        for command in calls
    )


@pytest.mark.parametrize(
    ("fault", "message"),
    [
        ("version", "installed version"),
        ("root", "installed root|provenance"),
    ],
    ids=["wrong-version", "wrong-root"],
)
def test_reinstall_rejects_wrong_installed_provenance_record(
    tmp_path: Path,
    fault: str,
    message: str,
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    if fault == "version":
        plugin_list_output = _plugin_list("3.0.0+codex.wrong", release)
    else:
        plugin_list_output = _plugin_list("3.0.0+codex.test", tmp_path / "wrong-plugin")

    with pytest.raises(RuntimeError, match=message):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(
                release,
                [],
                plugin_list_output=plugin_list_output,
            ),
        )


@pytest.mark.parametrize(
    "installed_skills",
    [
        PUBLIC_CODEX_SKILLS - {"scholar-using"},
        (PUBLIC_CODEX_SKILLS - {"scholar-using"}) | {"scholar-substituted"},
    ],
    ids=["missing-skill", "substituted-extra-skill"],
)
def test_reinstall_rejects_installed_cache_without_exact_public_skills(
    tmp_path: Path,
    installed_skills: set[str],
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)

    with pytest.raises(RuntimeError, match="exactly seven public skills"):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(release, [], installed_skills=installed_skills),
        )


def test_reinstall_rejects_nonprefixed_public_skill_in_installed_cache(
    tmp_path: Path,
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)

    with pytest.raises(RuntimeError, match="exactly seven public skills"):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(
                release,
                [],
                installed_skills=PUBLIC_CODEX_SKILLS | {"rogue"},
            ),
        )


def test_side_effect_free_validator_failure_preserves_compatibility_state(
    tmp_path: Path,
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    destination, before = _seed_compatibility_state(repo)

    with pytest.raises(RuntimeError, match="source-validator"):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(release, [], failing_step="source-validator"),
        )

    assert _compatibility_state(destination) == before


@pytest.mark.parametrize(
    "failing_step",
    ["marketplace-add", "cachebuster", "plugin-add", "post-validate"],
)
def test_every_failure_after_compatibility_removal_restores_exact_prior_state(
    tmp_path: Path,
    failing_step: str,
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    destination, before = _seed_compatibility_state(repo)
    operation_error = RuntimeError(f"{failing_step}-original")
    marketplace_list = (
        MARKETPLACE_HEADER + "other  /tmp/other\n"
        if failing_step == "marketplace-add"
        else None
    )

    with pytest.raises(RuntimeError, match=f"{failing_step}-original") as caught:
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(
                release,
                [],
                failing_step=failing_step,
                marketplace_list=marketplace_list,
                operation_error=operation_error,
                expect_compatibility_removed=True,
            ),
        )

    assert caught.value is operation_error
    assert _compatibility_state(destination) == before


def test_installed_cache_validator_failure_restores_exact_prior_compatibility_state(
    tmp_path: Path,
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    destination, before = _seed_compatibility_state(repo)

    with pytest.raises(RuntimeError, match="exactly seven public skills"):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(
                release,
                [],
                installed_skills=PUBLIC_CODEX_SKILLS - {"scholar-using"},
                expect_compatibility_removed=True,
            ),
        )

    assert _compatibility_state(destination) == before


def test_successful_marketplace_install_leaves_compatibility_discovery_absent(
    tmp_path: Path,
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    destination, _ = _seed_compatibility_state(repo)

    reinstall_codex_plugin(
        repo,
        marketplace,
        release,
        creator,
        runner=_runner(release, [], expect_compatibility_removed=True),
    )

    assert not (destination / ".evidraft-ownership.json").exists()
    assert not (destination / "scholar-paper").exists()
    assert not (destination / ".evidraft-private").exists()
    assert (destination / "scholar-custom" / "SKILL.md").read_bytes() == b"# user skill\n"


@pytest.mark.parametrize("failing_step", ["cachebuster", "plugin-add", "post-validate"])
def test_original_operation_error_wins_restore_cleanup_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failing_step: str,
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    manifest = release / ".codex-plugin" / "plugin.json"
    original = manifest.read_bytes()
    operation_error = RuntimeError(f"{failing_step}-original")
    cleanup_error = OSError("restore-cleanup")
    real_unlink = Path.unlink
    cleanup_attempts: list[Path] = []

    def fail_restore_cleanup(path: Path, missing_ok: bool = False) -> None:
        if _is_manifest_restore_temporary(path, manifest):
            cleanup_attempts.append(path)
            raise cleanup_error
        real_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_restore_cleanup)

    with pytest.raises(RuntimeError, match=f"{failing_step}-original") as caught:
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(
                release,
                [],
                failing_step=failing_step,
                operation_error=operation_error,
            ),
        )

    assert caught.value is operation_error
    assert caught.value.__cause__ is cleanup_error
    assert len(cleanup_attempts) == 1
    assert manifest.read_bytes() == original


def test_restore_bytes_preserves_write_error_when_cleanup_also_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "plugin.json"
    manifest.write_bytes(b"mutated")
    write_error = OSError("restore-write")
    cleanup_error = OSError("restore-cleanup")
    real_unlink = Path.unlink

    def fail_restore_write(_descriptor: int, _content: object) -> int:
        raise write_error

    def fail_restore_cleanup(path: Path, missing_ok: bool = False) -> None:
        if _is_manifest_restore_temporary(path, manifest):
            raise cleanup_error
        real_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(codex_install.os, "write", fail_restore_write)
    monkeypatch.setattr(Path, "unlink", fail_restore_cleanup)

    with pytest.raises(OSError, match="restore-write") as caught:
        codex_install._restore_bytes(manifest, b"original")

    assert caught.value is write_error
    assert caught.value.__cause__ is cleanup_error
    assert manifest.read_bytes() == b"mutated"


def test_success_propagates_restore_cleanup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    manifest = release / ".codex-plugin" / "plugin.json"
    original = manifest.read_bytes()
    cleanup_error = OSError("restore-cleanup")
    real_unlink = Path.unlink

    def fail_restore_cleanup(path: Path, missing_ok: bool = False) -> None:
        if _is_manifest_restore_temporary(path, manifest):
            raise cleanup_error
        real_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_restore_cleanup)

    with pytest.raises(OSError, match="restore-cleanup") as caught:
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(release, []),
        )

    assert caught.value is cleanup_error
    assert manifest.read_bytes() == original


@pytest.mark.parametrize("failing_step", ["cachebuster", "plugin-add", "post-validate"])
def test_reinstall_restores_base_manifest_after_failure(
    tmp_path: Path, failing_step: str
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    calls: list[list[str]] = []
    original = (release / ".codex-plugin" / "plugin.json").read_bytes()

    with pytest.raises(RuntimeError, match=failing_step):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(release, calls, failing_step=failing_step),
        )

    assert (release / ".codex-plugin" / "plugin.json").read_bytes() == original
    cachebusters = [command for command in calls if command[1].endswith("update_plugin_cachebuster.py")]
    assert len(cachebusters) == 1


@pytest.mark.parametrize("mode", ["deleted", "symlinked", "invalid-json"])
def test_reinstall_unconditionally_restores_manifest_after_invalid_cachebuster_output(
    tmp_path: Path,
    mode: str,
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    destination, compatibility_before = _seed_compatibility_state(repo)
    manifest = release / ".codex-plugin" / "plugin.json"
    original = manifest.read_bytes()
    external = tmp_path / "external-manifest.json"
    external.write_text(
        '{"name": "scholar", "version": "3.0.0+codex.external"}\n',
        encoding="utf-8",
    )
    external_before = external.read_bytes()

    def mutate(path: Path) -> None:
        if mode == "deleted":
            path.unlink()
        elif mode == "symlinked":
            path.unlink()
            path.symlink_to(external)
        else:
            path.write_text("{invalid json\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="cachebuster.*manifest"):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(
                release,
                [],
                cachebuster_action=mutate,
                expect_compatibility_removed=True,
            ),
        )

    assert manifest.read_bytes() == original
    assert not manifest.is_symlink()
    assert external.read_bytes() == external_before
    assert _compatibility_state(destination) == compatibility_before


def test_manifest_restore_ignores_precreated_predictable_symlink(tmp_path: Path) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    manifest = release / ".codex-plugin" / "plugin.json"
    original = manifest.read_bytes()
    external = tmp_path / "outside.txt"
    external.write_bytes(b"outside unchanged\n")
    predictable = manifest.with_name(
        f".{manifest.name}.restore-{codex_install.os.getpid()}"
    )
    calls: list[list[str]] = []

    def cachebust(path: Path) -> None:
        document = json.loads(path.read_text(encoding="utf-8"))
        document["version"] = "3.0.0+codex.test"
        path.write_text(json.dumps(document) + "\n", encoding="utf-8")
        predictable.symlink_to(external)

    reinstall_codex_plugin(
        repo,
        marketplace,
        release,
        creator,
        runner=_runner(release, calls, cachebuster_action=cachebust),
    )

    assert manifest.read_bytes() == original
    assert not manifest.is_symlink()
    assert external.read_bytes() == b"outside unchanged\n"
    assert predictable.is_symlink()
    cachebusters = [
        command for command in calls if command[1].endswith("update_plugin_cachebuster.py")
    ]
    assert len(cachebusters) == 1


@pytest.mark.parametrize(
    "plugin_list_output",
    [
        "scholar@scholar-ip-copilot available, enabled\n",
        "scholar@scholar-ip-copilot installed, disabled\n",
        "scholar@scholar-ip-copilot installed, enabled: false\n",
        "scholar@scholar-ip-copilot installed, not enabled\n",
        "other@scholar-ip-copilot installed, enabled\n",
        "scholar@scholar-ip-copilot-extra installed, enabled\n",
        "prefix-scholar@scholar-ip-copilot installed, enabled\n",
    ],
)
def test_reinstall_rejects_every_non_exact_installed_enabled_record(
    tmp_path: Path, plugin_list_output: str
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    original = (release / ".codex-plugin" / "plugin.json").read_bytes()

    with pytest.raises(RuntimeError, match="post-validate"):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(
                release,
                [],
                plugin_list_output=plugin_list_output,
            ),
        )

    assert (release / ".codex-plugin" / "plugin.json").read_bytes() == original


def test_reinstall_configures_repo_marketplace_before_cachebusting(tmp_path: Path) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    calls: list[list[str]] = []

    reinstall_codex_plugin(
        repo,
        marketplace,
        release,
        creator,
        runner=_runner(
            release,
            calls,
            marketplace_list=MARKETPLACE_HEADER + "other  /tmp/other\n",
        ),
    )

    add_marketplace = next(
        index
        for index, command in enumerate(calls)
        if command[-4:-1] == ["plugin", "marketplace", "add"]
    )
    cachebuster = next(
        index for index, command in enumerate(calls) if command[1].endswith("update_plugin_cachebuster.py")
    )
    assert calls[add_marketplace][-1] == str(repo.resolve())
    assert add_marketplace < cachebuster
    assert all(
        command[:3] == ["codex", "-c", 'model_reasoning_effort="xhigh"']
        for command in calls
        if command[0] == "codex"
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda document: document.update(name="wrong"), "unexpected marketplace name"),
        (
            lambda document: document["plugins"][0].update(
                source={"source": "github", "repo": "example/scholar"}
            ),
            "must be local",
        ),
        (
            lambda document: document["plugins"][0].update(
                source={"source": "local", "path": "./plugins/other"}
            ),
            "must be local",
        ),
        (lambda document: document.update(plugins=[]), "exactly one scholar entry"),
    ],
)
def test_invalid_marketplace_fails_before_commands(
    tmp_path: Path,
    mutation: Callable[[dict[str, object]], None],
    message: str,
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    document = json.loads(marketplace.read_text(encoding="utf-8"))
    mutation(document)
    marketplace.write_text(json.dumps(document), encoding="utf-8")
    calls: list[list[str]] = []

    with pytest.raises(ValueError, match=message):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(release, calls),
        )

    assert calls == []


def test_noncanonical_marketplace_fails_before_any_side_effect(tmp_path: Path) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    destination, compatibility_before = _seed_compatibility_state(repo)
    external_marketplace = tmp_path / "marketplace.json"
    shutil.copy2(marketplace, external_marketplace)
    manifest = release / ".codex-plugin" / "plugin.json"
    manifest_before = manifest.read_bytes()
    marketplace_before = marketplace.read_bytes()
    calls: list[list[str]] = []

    with pytest.raises(ValueError, match="canonical tracked marketplace"):
        reinstall_codex_plugin(
            repo,
            external_marketplace,
            release,
            creator,
            runner=_runner(release, calls),
        )

    assert calls == []
    assert _compatibility_state(destination) == compatibility_before
    assert manifest.read_bytes() == manifest_before
    assert marketplace.read_bytes() == marketplace_before
    assert external_marketplace.read_bytes() == marketplace_before


def test_release_drift_fails_before_any_side_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    destination, compatibility_before = _seed_compatibility_state(repo)
    manifest = release / ".codex-plugin" / "plugin.json"
    manifest_before = manifest.read_bytes()
    marketplace_before = marketplace.read_bytes()
    calls: list[list[str]] = []
    drift_calls: list[tuple[Path, Path]] = []

    def drift(source: Path, package: Path) -> list[str]:
        drift_calls.append((source, package))
        return ["changed: skills/scholar-using/SKILL.md"]

    monkeypatch.setattr(codex_install, "release_package_drift", drift, raising=False)

    with pytest.raises(ValueError, match="tracked release package has drift"):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(release, calls),
        )

    assert drift_calls == [(repo / "plugins/scholar-ip", release)]
    assert calls == []
    assert _compatibility_state(destination) == compatibility_before
    assert manifest.read_bytes() == manifest_before
    assert marketplace.read_bytes() == marketplace_before


@pytest.mark.parametrize(
    "kind",
    ["repo-root", "ancestor", "plugin-root", "release-descendant"],
)
def test_release_path_symlinks_fail_before_any_side_effect(
    tmp_path: Path,
    kind: str,
) -> None:
    build_root = tmp_path / "actual" if kind == "ancestor" else tmp_path
    repo, marketplace, release, creator = _build_release(build_root)
    destination, compatibility_before = _seed_compatibility_state(repo)
    presented_repo = repo
    presented_marketplace = marketplace
    presented_release = release
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_bytes(b"outside unchanged\n")

    if kind == "repo-root":
        presented_repo = tmp_path / "linked-repo"
        presented_repo.symlink_to(repo, target_is_directory=True)
        presented_marketplace = presented_repo / ".agents/plugins/marketplace.json"
        presented_release = presented_repo / "plugins/scholar"
    elif kind == "ancestor":
        linked_parent = tmp_path / "linked-parent"
        linked_parent.symlink_to(repo.parent, target_is_directory=True)
        presented_repo = linked_parent / repo.name
        presented_marketplace = presented_repo / ".agents/plugins/marketplace.json"
        presented_release = presented_repo / "plugins/scholar"
    elif kind == "plugin-root":
        external_release = outside / "scholar"
        shutil.copytree(release, external_release)
        shutil.rmtree(release)
        release.symlink_to(external_release, target_is_directory=True)
    else:
        skill = release / "skills/scholar-using/SKILL.md"
        external_skill = outside / "SKILL.md"
        shutil.copy2(skill, external_skill)
        skill.unlink()
        skill.symlink_to(external_skill)

    manifest = release / ".codex-plugin" / "plugin.json"
    manifest_before = manifest.read_bytes()
    marketplace_before = marketplace.read_bytes()
    outside_before = sentinel.read_bytes()
    calls: list[list[str]] = []

    with pytest.raises(ValueError, match="source.*symlink"):
        reinstall_codex_plugin(
            presented_repo,
            presented_marketplace,
            presented_release,
            creator,
            runner=_runner(release, calls),
        )

    assert calls == []
    assert _compatibility_state(destination) == compatibility_before
    assert manifest.read_bytes() == manifest_before
    assert marketplace.read_bytes() == marketplace_before
    assert sentinel.read_bytes() == outside_before


def test_missing_package_fails_before_commands(tmp_path: Path) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    (release / ".codex-plugin" / "plugin.json").unlink()
    calls: list[list[str]] = []

    with pytest.raises(FileNotFoundError):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(release, calls),
        )

    assert calls == []


def test_byte_identical_external_plugin_root_fails_before_commands(tmp_path: Path) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    external_release = tmp_path / "external-scholar"
    shutil.copytree(release, external_release)
    assert _compatibility_state(external_release) == _compatibility_state(release)
    calls: list[list[str]] = []

    with pytest.raises(ValueError, match="canonical tracked release package"):
        reinstall_codex_plugin(
            repo,
            marketplace,
            external_release,
            creator,
            runner=_runner(release, calls),
        )

    assert calls == []


def test_wrong_package_name_fails_before_commands(tmp_path: Path) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    manifest = release / ".codex-plugin" / "plugin.json"
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["name"] = "other"
    manifest.write_text(json.dumps(document), encoding="utf-8")
    calls: list[list[str]] = []

    with pytest.raises(ValueError, match="package name"):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(release, calls),
        )

    assert calls == []


def test_validate_rejects_package_without_exactly_seven_public_skills(tmp_path: Path) -> None:
    repo, marketplace, release, _ = _build_release(tmp_path)
    (release / "skills" / "scholar-using" / "SKILL.md").unlink()

    with pytest.raises(ValueError, match="exactly seven public skills"):
        validate_marketplace_plugin(repo, marketplace)


def test_validate_rejects_wrong_set_of_seven_public_skills(tmp_path: Path) -> None:
    repo, marketplace, release, _ = _build_release(tmp_path)
    (release / "skills" / "scholar-using").rename(
        release / "skills" / "scholar-unexpected"
    )

    with pytest.raises(ValueError, match="exactly seven public skills"):
        validate_marketplace_plugin(repo, marketplace)


def test_validate_rejects_nonprefixed_public_skill(tmp_path: Path) -> None:
    repo, marketplace, release, _ = _build_release(tmp_path)
    rogue = release / "skills" / "rogue" / "SKILL.md"
    rogue.parent.mkdir()
    rogue.write_text("# rogue\n", encoding="utf-8")

    with pytest.raises(ValueError, match="exactly seven public skills"):
        validate_marketplace_plugin(repo, marketplace)
