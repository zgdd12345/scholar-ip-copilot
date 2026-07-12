# Procedure — risk roll-up + suggested-revision recipe

## Risk roll-up

Per row, compute risk in two stages:

1. **Overlap-driven risk** = max over `prior_art_overlap[*].overlap_score` mapped as `identical → high, high → high, medium → medium, low → low, none → low`. An empty `prior_art_overlap` array (no prior art on the candidate at all) maps to `low`.
2. **No-support override**: if `spec_support == [] AND code_support == []`, force `risk = high` regardless of the overlap-driven value. An element with no support is its own risk: it is unenforceable and unanchored.

The two stages combine by `risk = max(overlap_driven, no_support_override)` where `high > medium > low`.

## Suggested-revision recipe

Populated **only** when `risk ∈ {medium, high}`; for `risk == low` the field is omitted (or set to `null`). For each populated row:

1. Pick the highest-scoring `prior_art_overlap` entry (ties broken by source order).
2. Read its `differentiator_note`.
3. Synthesize a one-line narrowing string of the form
   `Narrow \`<element fragment>\` to \`<fragment + differentiator>\`.` (See the example in [schemas.md](schemas.md).)
4. The string **must inherit a real differentiator** — never invent one not present in the prior-art bullet or the element's own support cells. If no differentiator is available, emit
   `Cannot auto-suggest revision; differentiator absent from prior_art_map.md.` and leave the row at its current risk.
5. **Never widens scope.** The suggested rewrite must contain the original fragment as a substring (or a strict refinement of it). The skill self-checks this: if the proposed string drops a noun present in the original element, abort and emit the "Cannot auto-suggest" fallback.

**Handoff.** Every row now has `risk` and (if applicable) `suggested_revision`. [procedure-write.md](procedure-write.md) renders the chart to disk.
