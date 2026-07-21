# Anti-patterns

- Inventing a paper, author, year, venue, or DOI that the API did not return.
- Skipping the cache check — every fetch must consult `.evidraft/literature/.cache/<provider>/` (see capability specification §"On-disk layout: disposable cache vs. durable snapshots", Tier 1).
- Running providers in parallel within one sub-query (race-condition on the rate-limit budget). See [provider-matrix.md](provider-matrix.md) §Rate-limit policy.
- Blending two providers' metadata into a single emitted row (use `aliases` instead). See [procedure.md](procedure.md) §6 dedup.
- Using `WebSearch` against a publisher paywall page (Springer / Elsevier / IEEE) — they do not honour API contracts; route to S2 / OpenAlex which already aggregate the metadata.
- Treating a 429 as "no results" — that is a transient failure, not an empty set. The retry/backoff rules in [provider-matrix.md](provider-matrix.md) §Rate-limit policy apply.
- Refreshing a stale Tier 1 provider JSON cache entry without first deleting it (the convention is delete-on-staleness for `.cache/<provider>/`).
- Deleting OR overwriting a Tier 2 `snapshots/<sha256>.md` file referenced by any row in `evidence.jsonl` — that is the durable backing for an immutable historical claim. To refresh a snapshot whose upstream page has changed, store the new raw body and emit a new evidence row with `supersedes` pointing at the prior row. See capability specification §Tier 2 refresh recipe.
