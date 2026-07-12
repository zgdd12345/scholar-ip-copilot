# Ethics block and refusal triggers

`workflow:polish.run` and other callers anchor here for the canonical refusal-flag list and the verbatim ethics statement.

## Ethics block (ships verbatim)

Every `.evidraft/style/humanize-<ts>.report.md` ends with the following block, **byte-identical**:

```
EviDraft humanize is a Williams-style polish tool, not a detector-evasion tool. Users MUST comply with venue AI-disclosure policies (ICML / NeurIPS / ACL / IEEE) and institutional authorship rules. The skill refuses if invoked with `--evade-detector` or similar flags.
```

The `workflow:polish.run` command also prints the shorter chat-line reminder ("EviDraft polish is a Williams-style style tool, not a detector-evasion tool. Your venue's AI-disclosure policy is your responsibility (ICML / NeurIPS / ACL / IEEE all require disclosure).") after writing the report.

## Refusal triggers

The command exits non-zero, the rewrite pass does not run, when **any** of:

- the invocation includes `--evade-detector`, `--bypass-gptzero`, `--humanize-for-detection`, `--fool-ai-detector`, `--evade-ai-detection`, or any string matching `(?i)(evade|bypass|fool|defeat).{0,20}(detect|gptzero|originality|turnitin)`;
- the chat-side request explicitly asks for detector evasion ("rewrite this so GPTZero doesn't flag it").

The refusal message echoes the verbatim ethics block above and lists the standard venue policies for ICML, NeurIPS, ACL, and IEEE.
