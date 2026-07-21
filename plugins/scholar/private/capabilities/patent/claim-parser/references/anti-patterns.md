# Anti-patterns

- **Rewriting claim text.** This skill parses and reports only. Edits to `claims.md` go through `claim-drafter` on a separate pass.
- **Inferring intent.** Do not write `"the inventor probably meant ..."` rows. Report the literal observation — `the index has no prior a index in c3 or c1` — and let a human decide.
- **Failing on legitimate but unusual formats.** Jepson claims (`A method, the improvement comprising ...`), product-by-process claims (`A product produced by the process of ...`), and means-plus-function claims (`means for ...ing`) are all valid; they get an INFO trace note in the `.log` but never a `fail` from this skill.
- **Reading outside `.evidraft/patent/`.** No bib, no manuscript, no code. The only optional input is `invention_disclosure.md` and only for `TERMINOLOGY_DRIFT` (see [warning-taxonomy.md](warning-taxonomy.md)).
- **Timestamping `claims_parsed.json`.** It is the canonical current view; consumers always read the latest. The `.log` is the timestamped audit trail.
- **Inventing antecedents.** If a noun phrase is ambiguous (`the system` could mean half a dozen things), do **not** guess which earlier introduction it points to — fire `ANTECEDENT_MISSING` and let the attorney disambiguate.
- **Treating this as legal review.** Structural only — see the "Advisory-only framing" section in capability specification.
