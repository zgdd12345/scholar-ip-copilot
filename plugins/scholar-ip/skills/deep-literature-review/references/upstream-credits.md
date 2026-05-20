# Upstream credits

Idea-level borrowings only; no upstream code is imported.

- **STORM** — perspective-guided retrieval; we borrow the per-perspective sub-query split at Stage 1.
- **GPT-Researcher** — per-section sub-agent dispatch; we borrow the one-sub-agent-per-stage pattern.
- **dzhng/deep-research** — breadth/depth knobs; we expose the same two user-facing controls.
- **Open Deep Research** — structured research brief; we adopt the explicit `plan.yaml` artefact instead of an implicit prompt.
- **open-paper-machine** — PRISMA-style screening log shape; we adopt `id, score, decision, reason` as the canonical CSV.
- **ASReview, Rayyan, open-paper-machine** — PRISMA discipline (every drop has a reason; no silent rejects) inspires Stage 3.
