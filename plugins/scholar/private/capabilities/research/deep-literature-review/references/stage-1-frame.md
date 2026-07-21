# Stage 1 - Frame

**Inputs.** Use an explicit `topic` first, then project metadata, then an advisory scope
research question. Scope is advisory and its absence does not block framing. If no topic
can be resolved from any source, return `blocked` without inventing one.

**Procedure.**

1. Read available project and scope context without requiring either file.
2. Derive the research question, bounded sub-queries, inclusion and exclusion terms,
   year window, venue allow-list, and language allow-list.
3. Cap sub-query expansion at `breadth`; do not treat the cap as a target.
4. Write `plan.yaml` with an input summary and any missing-context note.

```yaml
run_id: <utc-timestamp>
topic: <string>
research_question: <string>
sub_queries:
  - id: q1
    text: <string>
    perspective: method | dataset | theory | application | evaluation | critique
filters:
  year_range: [<int>, <int>]
  venues: [<string>, ...]
  languages: [en]
inclusion_keywords: [<string>, ...]
exclusion_keywords: [<string>, ...]
breadth: <int>
depth: <int>
providers: [arxiv, semantic-scholar, openalex]
mode: fast | full
input_summary: <stable summary used for reuse>
notes: [<advisory gap>, ...]
```

**Handoff.** Stage 2 reads `plan.yaml` only.
