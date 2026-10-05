---
name: result
pack: lab
format: markdown
path: content/results/R-{n}.md
id: prefix:R
skeleton: skeleton.md
lives: permanent
states: [live, superseded, retracted]
fields:
  - { name: protocol, type: id, genre: protocol, status: [locked, abandoned], required: true }
  - { name: number, type: string, required: true }
  - { name: baseline, type: string, required: true }
  - { name: bound, type: string, required: true }
  - { name: evidence, type: path, required: true }
  - { name: rederive, type: string, required: true }
  - { name: date, type: date, required: true }
  - { name: supersedes, type: id, genre: result }
checks:
  require: [why]
  max_words: 150
on_map: optional
---

# Result

A result is one measured number, with its baseline, its bound, where its evidence is, and the command that re-derives it: the one home every page cites.

## Reader

Anyone about to cite the number, and anyone who doubts it. The first wants the value and its limits in one place. The second wants the evidence and the command, to check it themselves.

## Voice

Terse and numeric. The title is a plain sentence carrying the number. The bound sits beside the number, never in a later paragraph.

> The RMS error of the pi estimate fell with a fitted log-log slope of -0.493.

## Metadata

The front matter is the result. It holds `title`, `description`, `genre`, `id` and `tags`, never `status`: the engine derives it. The `title` is a plain sentence carrying the number. The `description` says in one line what was measured and against what. These fields are all required:

- `protocol`: the slug of the locked protocol the run followed. If that protocol is later `abandoned`, the result stays valid.
- `number`: the value with its denominator, as a string, exactly as `rederive` prints it. A tool may compare the two character for character, after trimming whitespace.
- `baseline`: what it is compared against, measured on the same inputs.
- `bound`: one sentence on where the number holds and where it says nothing.
- `evidence`: the path of the file or folder holding the raw measurement, resolved from the charter's `root`.
- `rederive`: the command that prints the number from the evidence, run from the charter's `root`.
- `date`: the day the number was recorded, `YYYY-MM-DD`.

One field is optional:

- `supersedes`: the id of the result this one corrects. The engine marks that result `superseded` and shows a banner on it linking this one.

## Shape

The shell draws the title, the description, the derived status and the fields above the body. The body has one required section, `## Why it matters` (`why`): one or two sentences. An optional `## Notes` section records exclusions or anomalies. The argument about what the number means goes in a report, not here.

## Forbidden

- A missing field. Caught by `fields`.
- A protocol that does not exist, or is neither `locked` nor `abandoned`. Caught by `fields`, through the `protocol` field's limits.
- An evidence path that does not exist. Caught by `fields`, through the `path` type.
- A `status` written in the front matter. Caught by `fields`; the status is derived.
- Two numbers in one result. Judged, not checked; record two results.
- Any change after the first commit. Caught by `permanent`.
- A number copied from a summary or a journal entry. Judged, not checked; run the command and write what it prints.

## Steps

- Re-derive the number yourself, by running `rederive` from the charter's `root`, before writing it down. Write exactly what the command printed.
- Give it the next free id with `folio new result`. Never pick a number by hand.
- Write the bound in the same breath as the number: size, setting, what was not measured.
- To correct a result, record a new one with `supersedes`. Never open the old file.
- To retract a result that nothing replaces, add a journal entry: `folio journal add --kind retraction --about R-n --title ".." --description ".." --body ".."`. The body says why.
- No list needs a line for it. The protocol it names shows it in a generated panel.

## Lifecycle

Permanent: never edited once committed. Its status is derived, never written. It is `live` from its first commit. It is `superseded` once a later result names it in `supersedes`, and `retracted` once a journal entry of kind `retraction` names it in `about`. Either way the engine shows a banner on it, linking the newer result or the entry. It is never `retired` and never redirected. Its id and its file stay forever, so old citations still resolve and still show what they cited. The rule `cites-superseded` then names every revised page that still cites it.

Whether a number may be recorded at all is not folio's call. lab-kit decides it, at promotion, by re-deriving from the evidence; without lab-kit, the owner decides.

## Example

```markdown
---
title: The RMS error of the pi estimate fell with a fitted log-log slope of -0.493
description: The slope of the RMS error over 100 seeds against the number of points, over five sizes.
genre: result
id: R-2
tags: [monte-carlo, convergence]
protocol: pi-error-scaling
number: "-0.493"
baseline: the theoretical slope of -0.5, for independent points
bound: 64 to 16,384 points, 100 seeds per size, Python's standard generator; one estimator only.
evidence: experiments/pi-error-scaling/out/estimates.tsv
rederive: python3 experiments/pi-error-scaling/bin/fold.py experiments/pi-error-scaling/out/estimates.tsv --stat slope
date: 2026-10-04
supersedes: R-1
---

## Why it matters

The protocol's measure is the RMS error, and this is its slope. It corrects `R-1`, which fitted the mean absolute error and got -0.483.
```
