# Anti-patterns

- Claiming novelty because the search returned zero hits — that means "not found", not "does not exist". Always include the ethics disclaimer.
- Declaring a candidate "patentable" or "non-infringing". This skill writes prior art; the attorney writes verdicts.
- Hammering Google Patents faster than 1 req/sec or scraping > 50 result pages — both risk a polite-block from the host.
- Inlining `EPO_OPS_KEY` in a URL or shell argument; always read from env.
- Merging two providers' field values into one row (use `aliases`).
- Treating a 429 as "no results" — that is a transient failure; retry per the policy above.
- Skipping the cache check (re-fetching the same patent number across runs wastes the polite-pool budget).
- Reading a patent PDF behind a paywall — public patent databases already publish the metadata; use them, not the paywall.
