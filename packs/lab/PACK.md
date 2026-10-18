---
name: lab
version: 0.1.0
requires: { folio: ">=0.1.0" }
genres: [question, protocol, result, claim, report]
workflows: [record-a-result, write-a-report]
rules: rules.md
journal_kinds: [lock, run, kill, instrument, pivot]
---

# Lab

This pack is for work that tests ideas against evidence: it gives questions, plans, measured numbers, claims and plain-English reports each a home with an id.

## What it adds

- **question**: an open research question, ranked, with what would settle it. Its page shows, in a generated panel, every protocol that names it. Ids `Q-1`, `Q-2`, and so on. States: `draft`, `live`, `narrowed`, `answered`, `dropped`.
- **protocol**: the plan for one experiment, written and locked before it runs, and frozen once locked. Its page shows the results that name it. The hypothesis, the intuition, the one variable, the pinned configuration, the allowed moves, the measures, the decision rules `D1`... with the kill rule marked, and the predictions `P1`... with confidences. States: `draft`, `locked`, `abandoned`.
- **result**: one measured number, with its baseline, its bound, its evidence, the command that re-derives it, its protocol and its date. Ids `R-1`, `R-2`. Permanent: never edited once committed. A new result supersedes a wrong one, and a `retraction` journal entry retracts one. Its status is derived: `live`, `superseded` or `retracted`.
- **claim**: what may be said, and how strongly, citing the results behind it. Ids `C-1`, `C-2`.
- **report**: one experiment's outcome in plain English, for someone who was not there, with nulls as prominent as wins. Frozen once `live`; a correction is a journal entry about it, shown as a banner.
- **record-a-result** (workflow): a number, its evidence and its protocol in; a result out, shown on its protocol and logged in the journal.
- **write-a-report** (workflow): a set of results in; a report out, on a map.
- **Every number cites a result** (rule, check `uncited-number`). A number that reports a measurement links the result that holds it.
- **A citation names a current result** (rule, check `cites-superseded`). A revised document that cites a superseded or retracted result is flagged.
- **Journal kinds** `lock` (a protocol locked), `run` (a run launched, checkpointed, failed or ended), `kill` (a kill rule fired), `instrument` (a change to how the lab measures) and `pivot` (a change of direction). They join the core's four (`decision`, `lesson`, `correction`, `retraction`) while the pack is on.

A result's evidence and its re-derive command usually sit outside the library, in the project around it. They resolve from the charter's `root`, so set `root` to the project root when the library is a folder inside it.

## What this pack does not do

The pack holds documents only. It never decides whether a result counts.

folio checks the shape of each document: its fields, its sections, its status words and its citations. A locked protocol is frozen, and folio checks its bytes against the first commit that locked it. folio does not run a re-derive command, score predictions, or decide that a number may be recorded.

Those calls belong to whoever runs the lab. lab-kit, a separate tool built on folio, switches this pack on and adds them: the method, the record of each lock (a journal entry of kind `lock`), the re-derivation at promotion, the scoring. Without lab-kit, the owner makes those calls, and the cards and workflows say where: the protocol card says how to lock and record the lock, record-a-result asks whether a number may be recorded, and write-a-report scores the protocol in the report.

## When to switch it on

Switch it on when the library reports measurements: benchmark runs, experiments, field trials, timings. A lab needs it. So does a project that tracks performance numbers across changes.

Without it, a number lives wherever someone typed it. Two pages can quote different values for the same measurement, and nothing notices. You lose the line between a plan made before the run and a story told after it.

## What switching it on changes

Nothing is rewritten. The pack adds five genres, two workflows and five journal kinds.

The `uncited-number` rule reads existing pages and papers. It names every number that looks like a measurement and cites no result. It starts as a warning, so the gate still passes.

The organise skill then proposes fixes, one page at a time. Usually that means recording the number as a result through record-a-result, then citing it. A number that is not a measurement is marked as such. You approve each fix. Once the warnings are cleared, the charter can make the check an error.

## Working with other packs

- **With the knowledge-base pack.** A number quoted from someone else's work cites the source it came from, and `uncited-number` accepts that. Your own measurements are results, never sources.
- **The journal is core.** The lab writes into the library's one journal. A run's raw numbers may appear there first; a journal entry is a record, so the rule does not flag it.
- **The paper is core.** With this pack on, every measured number in a paper carries `\fcite{R-n}`.
- **Concepts stay clean.** A concept's definition cites no result, so it survives when the numbers change. Cite results below the definition, not inside it.
