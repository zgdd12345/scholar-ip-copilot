"""EviDraft deterministic project core."""

__version__ = "2.0.0"

from .core import (
    EvidenceError,
    FinalizeResult,
    MigrationError,
    MigrationResult,
    PreflightError,
    PreflightResult,
    append_evidence,
    detect_format_version,
    is_sensitive_path,
    migrate_project,
    prune_retention,
    resolve_evidence,
    scope_policy,
    store_snapshot,
    workflow_finalize,
    workflow_prepare_output,
    workflow_preflight,
)

__all__ = [
    "EvidenceError",
    "FinalizeResult",
    "MigrationError",
    "MigrationResult",
    "PreflightError",
    "PreflightResult",
    "append_evidence",
    "detect_format_version",
    "is_sensitive_path",
    "migrate_project",
    "prune_retention",
    "resolve_evidence",
    "scope_policy",
    "store_snapshot",
    "workflow_finalize",
    "workflow_prepare_output",
    "workflow_preflight",
]
