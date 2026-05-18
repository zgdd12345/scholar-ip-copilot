<!-- ILLUSTRATIVE EXAMPLE -- /scholar:patent-review output. Fictional. -->

# Patent review report

Generated: 2026-03-04T11:00:00Z
Targets:
- disclosure: .evidraft/patent/invention_disclosure.md
- claims:     .evidraft/patent/claims.md
- chart:      .evidraft/patent/claim_chart.md

## 1. Patent engineer

- **Gaps**:
  - Section 7 (Implementation) cites only `src/optim/scheduler.py`. The
    caller code that applies $(\eta_t, m_t)$ to a real optimiser is not
    in the example; the disclosure must say so explicitly.
  - The numerical example in Section 10 references ev_0104 only
    (engineering log). A reproducible experiment record would
    strengthen the disclosure.
- **Suggestions**:
  - Add a worked example with `coupling_alpha = 0.0` and
    `coupling_alpha = 1.0` to show the degenerate cases.
  - Expand the diagram suggestions in Section 11 with a pseudocode
    block.

## 2. Claim drafter

- **Antecedent / consistency issues**:
  - Claim 1[c] uses "the ratio $\eta_t / \eta_0$" -- "the ratio" is the
    first mention. Recite "a ratio" first, then "the ratio".
  - Terminology drift between the disclosure ("coupling weight") and
    the candidate file ("coupling_alpha"); pick one and use it
    everywhere.
- **Dependent-claim narrowness check**:
  - Claim 2 (power blend) is genuinely narrower (different blend
    function).
  - Claim 3 (per-group $\alpha$) is genuinely narrower.
  - Claim 4 (linear warmup of momentum) is genuinely narrower.
- **Suggestions**:
  - Consider an apparatus claim mirroring the method claim, and a
    computer-readable-medium claim, for US scope.

## 3. Novelty critic

- **Per-element prior-art overlap**:
  - 1[b] cosine LR envelope: overlaps PA-01 (cosine schedule with
    momentum warmup).
  - 1[c] momentum as blend keyed off $\eta_t/\eta_0$: partial overlap
    with PA-02 (independent momentum decay) but PA-02 does not key
    momentum off the LR ratio.
  - 1[d] $\alpha = 0$ recovers constant momentum: no overlap flagged;
    this is the distinguishing language.
  - 1[e] applying to SGD update: standard; not itself novel.
- **Distinguishing language suggestions**:
  - Add "wherein $m_t$ is computed as a function of $\eta_t / \eta_0$
    and $\alpha$" to make the dependency explicit at the claim level.

## 4. Methodology / technical reviewer

- **Code vs disclosure mismatches**:
  - Disclosure Sec. 6 says the blend is
    $\alpha (\eta_t / \eta_0) + (1 - \alpha)$ -- this matches
    `src/optim/scheduler.py:72` (ev_0102). OK.
  - Disclosure Sec. 6 says warmup is a *cosine* warmup
    ($\tfrac{1}{2}(1 - \cos(\pi t / T_w))$) while the
    "momentum rises linearly" -- both match
    `src/optim/scheduler.py:48-73`. OK.
- **Recommendations**:
  - Move the momentum-floor / base-momentum names out of the YAML
    config name space and into the spec to avoid drift.

## 5. Skeptical examiner

- **Strongest rejection scenario**:
  - 102 (anticipation) over PA-01: examiner argues that PA-01 already
    teaches a cosine LR schedule with a momentum schedule, and that
    "coupling weight" is a labelling difference.
- **Suggested amendments**:
  - Recite 1[c] more concretely: "wherein the momentum coefficient
    $m_t$ is computed as $m_{\min} + (m_0 - m_{\min}) \cdot [\alpha
    (\eta_t / \eta_0) + (1 - \alpha)]$".
  - Add a means-plus-function-free apparatus claim that recites the
    same formula.

## Overall verdict

- **Verdict**: NEEDS_WORK

- **Top-3 next actions**:
  1. Resolve terminology drift between "coupling weight" and
     `coupling_alpha`; pick one term and propagate through disclosure,
     claims, and claim chart.
  2. Replace claim 1[c] with the explicit blend formula to harden
     against a PA-01 anticipation rejection.
  3. Add a worked example with $\alpha = 0$ and $\alpha = 1$ in
     Disclosure Sec. 10 to show the degenerate cases.
