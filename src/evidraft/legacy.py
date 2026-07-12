"""Closed v1 identifier sets used only for ownership-safe upgrades."""

V1_COMMANDS = frozenset(
    {
        "brainstorming", "deepresearch", "paper-check", "paper-code-audit",
        "paper-draft", "paper-experiment", "paper-idea", "paper-init", "paper-lit",
        "paper-review", "paper-venue", "patent-claims", "patent-disclosure",
        "patent-init", "patent-prior-art", "patent-review", "patent-scout", "polish",
        "reading-list", "using-deep-research", "using", "xreview",
    }
)
V1_AGENTS = frozenset(
    {
        "brainstormer", "claim-drafter", "codebase-analyst", "consistency-checker",
        "deep-research-orchestrator", "evidence-auditor", "experiment-analyst",
        "latex-editor", "literature-reviewer", "methodology-reviewer", "novelty-critic",
        "paper-critic", "patent-engineer", "prose-polisher", "screener",
    }
)
V1_SKILLS = frozenset(
    {
        "bib-audit", "bib-manager", "brainstorming", "claim-chart-builder",
        "claim-parser", "code-intel", "codebase-audit", "deep-literature-review",
        "evidence-check", "experiment-analysis", "external-agent-bridge", "humanize",
        "latex-build", "latex-style-audit", "latex-writing", "literature-review",
        "novelty-heuristics", "patent-claims", "patent-disclosure", "patent-search",
        "scholar-search", "using-deep-research", "using-scholar-ip-copilot",
        "venue-formatting", "xref-audit",
    }
)
V1_HOOK_FILES = frozenset(
    {
        "_lib.sh", "citation-guard.sh", "command-hooks.json", "hooks.json",
        "scope-required.sh", "session-start.sh",
    }
)
