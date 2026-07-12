---
id: venue-formatting
title: "Convert an arXiv-style manuscript into a target venue's template"
kind: skill
phase: paper
description: >
  Load when workflow:paper.venue runs, or when workflow:paper.draft is invoked with a
  non-default style. Provides the conversion procedure from the neutral
  arXiv manuscript/ tree into submissions/<venue>/, plus one YAML spec per
  supported venue describing documentclass, required packages, page limits,
  anonymisation requirements, caption conventions, and where to fetch
  class files. The spec files live under venues/<id>.yaml and are read by
  the procedure below.
triggers:
  - "workflow:paper.venue"
  - "workflow:paper.draft with non-default style"
  - "submission preparation"
  - "double-blind anonymisation"
provides:
  - venue-spec-format
  - venue-conversion-procedure
  - anonymisation-recipe
  - page-limit-check
  - per-venue-yaml-specs
allowed_tools: [Read, Glob, Grep, Write, Edit, "Bash:cp*", "Bash:latexmk*"]
policies: [evidence-integrity]
references:
  - doc: capability:latex-writing
  - doc: capability:evidence-check
  - doc: capability:latex-build
---

# venue-formatting

## When to use

Load when running `workflow:paper.venue` (the dedicated conversion command) or `workflow:paper.draft` with a non-default `style` argument. The manuscript at `manuscript/` is **always** arXiv-neutral; this skill produces a parallel `submissions/<venue>/` tree without modifying the source.

## Inputs

- `manuscript/main.tex`, `manuscript/sections/*.tex`, `manuscript/references.bib`
- `manuscript/figures/*` (or wherever the project keeps figure assets)
- `capability:venue-formatting/venues/<id>.yaml` (the venue spec — required)
- target venue's class file (`.cls`) — not vendored; user fetches from publisher
- `.evidraft/project.yaml` (authors, target_venue, language)

## Outputs

- `submissions/<venue>/main.tex`
- `submissions/<venue>/sections/`
- `submissions/<venue>/references.bib` (copy of the canonical bib)
- `submissions/<venue>/MANIFEST.md` (resolved spec, compile status, page count, change list, missing assets)

## Procedure

### 1. Venue spec format

Each `venues/<id>.yaml` declares the fields the conversion procedure reads. Required keys:

```yaml
id: <kebab-case>
name: "<human venue name>"
documentclass: '\documentclass[<opts>]{<class>}'
class_files_url: "<publisher URL or local path placeholder>"
bib_style: <natbib|biblatex|IEEEtran|ACM-Reference-Format|plainnat|ieeenat_fullname|...>
anonymous_review: <true|false>
page_limit:
  main: <integer|unlimited>           # main paper pages
  refs: <integer|unlimited>           # references budget
  supplement: <integer|unlimited|n/a> # supplementary if separate
column_layout: <one-column|two-column>
font_size: <10pt|11pt|12pt>
usepackage_required: [<pkg>, ...]
usepackage_forbidden: [<pkg>, ...]
caption_convention: "<one-line description>"
section_numbering: <yes|no>
line_numbers_for_review: <true|false>
notes: "<one paragraph of human-readable instructions>"
```

The procedure below reads these keys; any new key added to a spec file becomes a hint to be acted on under "venue-specific tweaks".

### 2. Conversion procedure

1. **Resolve the spec.** Read `capability:venue-formatting/venues/<venue>.yaml`. If the file is missing, abort with an error pointing to the supported list in `plugin.yaml::paper_defaults.supported_venues`.

2. **Mirror the manuscript.** Copy `manuscript/` -> `submissions/<venue>/` (use `cp -R` or equivalent). The original `manuscript/` is **never** edited by this skill.

3. **Rewrite `main.tex` preamble.**
   - Replace `\documentclass{...}` with the spec's `documentclass`.
   - Remove any `\usepackage{<pkg>}` lines in `usepackage_forbidden`.
   - Add `\usepackage{<pkg>}` lines for each entry in `usepackage_required` that is not already present.
   - Replace `\bibliographystyle{...}` with the spec's `bib_style` (or switch to `biblatex` `\printbibliography` setup if the spec mandates).
   - Leave section-prose `.tex` files alone — preamble-only rewrite is the rule.

4. **Author / affiliation block.**
   - If `anonymous_review: true`, replace the author block with the venue's anonymous form (commonly `\author{Anonymous}` or the class's `\anonymous` macro per the spec `notes`).
   - Otherwise apply `.evidraft/project.yaml::authors` to the venue's author macro.

5. **Anonymisation pass (if `anonymous_review: true`).** See §3 below.

6. **Class-file handling.** Do **not** vendor `.cls` / `.sty` files. Instead, write a clear note in `MANIFEST.md` pointing to `class_files_url`, and warn the user that compile will fail until they fetch the class kit (typical Overleaf / publisher author-kit zip).

7. **Compile sanity check.** Call the `latex-build` skill on `submissions/<venue>/main.tex` (it wraps `latexmk -pdf -interaction=nonstopmode` and writes a structured `errors.json`). If `latexmk` is not installed in this environment, mark compile `SKIPPED` and continue.

8. **Page-limit check.** If `page_limit.main` is an integer, compute the rendered page count of the body (excluding references) and compare. Warn if over. Use the class's own counting if the venue mandates a particular method (some venues count references in the main budget — read `notes`).

9. **Write `MANIFEST.md`.**

   ```
   # Submission manifest: <venue>

   - source: manuscript/main.tex
   - venue spec: capability:venue-formatting/venues/<venue>.yaml
   - documentclass applied: <...>
   - bib style: <...>
   - anonymisation: on/off
   - class file present: yes/no (URL: <class_files_url>)
   - compile: PASS / FAIL / SKIPPED
   - page count vs limit: <m> / <limit>
   - missing assets: ...
   - changes vs manuscript/:
     - preamble: ...
     - author block: ...
     - removed packages: ...
     - added packages: ...
   ```

### 3. Anonymisation recipe

For double-blind venues (`anonymous_review: true`):

- Replace author block with the venue's anonymous form.
- Move `\acknowledgments` / funding / institutional thanks to a separate `acknowledgements.tex` file that is **not** `\input`-ed during review. Add an `\if<flag>...\fi` switch only if the venue's class supports it.
- Strip URLs that identify authors or affiliations: GitHub repos, personal sites, internal trackers. Replace with `\textit{(URL withheld for review)}`.
- Replace self-citation patterns ("In our previous work [12], we …") with neutral phrasing ("Prior work [12] introduced …"). The self-cite stays in the bibliography but the prose does not name it as "ours".
- If a venue allows non-anonymous supplementary material that is excluded from review, that policy is recorded in the spec `notes`; do **not** make this judgement automatically — read the spec.
- Search prose for first-person identifiers that could leak: lab name, project codename, dataset name that is uniquely the authors' (rename to a generic identifier and footnote).
- If `submissions/<venue>/supplement/` exists and the venue's double-blind policy covers it, anonymise there too.

### 4. Page-limit check

- `page_limit.main: 8` means the **main paper** is at most 8 pages; references typically have their own budget (`refs: unlimited` is common at CV / ML conferences but explicitly capped at some venues).
- `page_limit.refs: unlimited` permits any reference count.
- `page_limit.refs: 0` means references count toward main (rare; spec `notes` will say so).
- Compute counts from the compiled PDF (last page number minus first page of references for main; references span for refs). If compile is `SKIPPED`, mark counts `UNKNOWN`.

### 5. Per-venue YAML specs

All specs live at `capability:venue-formatting/venues/<id>.yaml`. The MVP set:

| id | Venue |
|---|---|
| `arxiv` | arXiv preprint (default neutral) |
| `cvpr` | IEEE/CVF Computer Vision and Pattern Recognition |
| `iccv` | IEEE/CVF International Conference on Computer Vision |
| `eccv` | European Conference on Computer Vision |
| `neurips` | Conference on Neural Information Processing Systems |
| `icml` | International Conference on Machine Learning |
| `iclr` | International Conference on Learning Representations |
| `emnlp` | Empirical Methods in Natural Language Processing |
| `acl` | Annual Meeting of the ACL |
| `aaai` | AAAI Conference on Artificial Intelligence |
| `ieee` | IEEEtran (transactions / generic IEEE) |
| `acm-generic` | ACM `acmart` template (generic) |
| `generic` | Plain `article` fallback when no specific venue is known |

URLs in `class_files_url` are placeholders that point to publisher author kits. **Class files are never vendored**; the user must download them from the publisher (Overleaf templates linked in the venue `notes` field are the common shortcut).

## Quality checklist

- [ ] `manuscript/` is untouched.
- [ ] `submissions/<venue>/` mirrors `manuscript/`.
- [ ] Preamble rewritten per spec; section prose unchanged.
- [ ] Anonymisation applied if `anonymous_review: true`.
- [ ] `MANIFEST.md` lists every change vs `manuscript/`.
- [ ] Compile status recorded (PASS / FAIL / SKIPPED).
- [ ] Page count vs limit recorded.
- [ ] Class files not vendored; manifest tells the user where to get them.

## Anti-patterns

- Editing `manuscript/` in place "for the venue". Always operate on the `submissions/<venue>/` copy.
- Vendoring publisher class files. They are usually licensed for use in submissions but not redistribution.
- Anonymising the canonical `manuscript/` — anonymisation belongs to the venue copy only.
- Adding venue-specific commands (`\cvprfinalcopy`, `\acmConference{...}`) into `manuscript/`.
- Skipping the page-limit check because compile is `SKIPPED`. Record `UNKNOWN` and warn the user.
- Letting `usepackage_forbidden` collide silently with a package the manuscript actually needs (e.g., the venue forbids `hyperref` for camera-ready). Flag the conflict in `MANIFEST.md` and stop, do not silently remove.
- Auto-submitting anywhere. The skill produces files; the user submits.
