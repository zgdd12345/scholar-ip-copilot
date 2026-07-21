"""EviDraft deterministic project core."""

__version__ = "3.0.0"

from .core import (
    EvidenceAuditResult,
    EvidenceError,
    FinalizeResult,
    MigrationError,
    MigrationResult,
    PreflightError,
    PreflightResult,
    append_evidence,
    audit_evidence,
    detect_format_version,
    is_sensitive_path,
    migrate_project,
    prune_retention,
    resolve_evidence,
    store_snapshot,
    workflow_finalize,
    workflow_prepare_output,
    workflow_preflight,
)

__all__ = [
    "EvidenceAuditResult",
    "EvidenceError",
    "FinalizeResult",
    "MigrationError",
    "MigrationResult",
    "PreflightError",
    "PreflightResult",
    "append_evidence",
    "audit_evidence",
    "detect_format_version",
    "is_sensitive_path",
    "migrate_project",
    "prune_retention",
    "resolve_evidence",
    "store_snapshot",
    "workflow_finalize",
    "workflow_prepare_output",
    "workflow_preflight",
]
