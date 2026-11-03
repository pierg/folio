---
name: report
pack: lab
format: html
path: content/reports/{slug}/index.html
id: slug
skeleton: skeleton.html
lives: frozen
states: [draft, live, historical]
frozen_in: [live, historical]
frozen_exits: [historical]
checks:
  cites: results
on_map: required
---

# Report

A report tells one experiment's outcome in plain English to someone who was not there, frozen once published, nulls as prominent as wins.

## Reader

A sharp outsider who has never seen the work. They read carefully but know none of its shorthand. They want to know what was asked, what happened and how far to trust it.

## Voice

Plain. Short sentences, words the reader already has, and every term of art linked to its concept. Ids ride beside the numbers they license, as links, and are never the subject of a sentence. A miss is stated as plainly as a hit.

> We expected the error at each size to sit within 10% of theory. It did not: at one size it left that band.

## Metadata

No fields beyond the core. The `title` is the outcome, in one plain line. The `description` says in one line what was tested and on what.

## Shape

The shell draws the title, the description, the status and the dates above the body. The generated panels list every result, protocol, question and claim the report cites, what cites it, and the journal entries about it. So the body has no list of links. Below the header the page is a canvas: a report can lead with the figure that carries its answer.

What a good report covers, usually in this order, judged, not checked:

1. **The question, in words**: what was asked, in one short paragraph, linking the question it serves.
2. **What we expected, and why**: the protocol's intuition in plain words, then the hypothesis and predictions as they stood before the run. Link the protocol.
3. **What we did**: what was run: the setup, the one variable and its arms, and what was held fixed. Any voided run or re-run is said plainly here.
4. **What happened**: the results, each number citing its result by id, and how each decision rule (`D1`...) and each prediction (`P1`...) came out.
5. **What we learned**: why it did or did not work. Not a restatement of the numbers.
6. **What this does not show**: every bound the results carry, what was not measured, and what is untested rather than disproven.

Figures come from `assets/figures/`, the same files any sibling page or paper uses.

## Forbidden

- Any edit once `live`, other than a commit that changes only the status to `historical`. Caught by `frozen`, which compares with the first commit that set `live`, so going back to `draft` does not unfreeze it.
- A list of links that only repeats the generated panels. Judged, not checked.
- A number that cites no result. Caught by `uncited-number`.
- A report that cites no result. Caught by `cites: results`.
- A null or a miss told more quietly than a win: later, shorter, or hedged. Judged, not checked.
- An id, a file path or a command as the subject of a sentence. Judged, not checked.
- A bound from a result left unsaid. Judged, not checked.
- A sentence a claim's "Must not be said" forbids. Judged, not checked.
- A rolling update: new runs added to an old report. Judged, not checked; a new experiment gets its own report.

## Steps

- Read the locked protocol before writing "What we expected". Write the expectation as it stood then, never as the outcome makes it look.
- Use `folio cite R-n` for every result link.
- Score the protocol here. "What happened" marks each decision rule and prediction hit or miss, by id, against the protocol as locked. When lab-kit runs the lab, state its review's scoring; without it, the owner confirms the scoring before the report is published.
- Hold the report as `draft` while writing it (`folio new report <slug> --status draft`), and a report is frozen once `live` is committed.
- Reuse the figures in `assets/figures/`. Never redraw one for the report.
- Read the claims that cite these results, and stay inside them.

## Lifecycle

Frozen. Written once, after the results are recorded, then published by setting its status to `live`. From then on it is never rewritten (check `frozen`). When a result it cites is superseded or retracted, the result's own banner says so; the report is not flagged by `cites-superseded`. When the report itself needs a correction, add a journal entry of kind `correction` about it, saying what changed. The shell shows it as a banner on the report. If the report's main point no longer holds, also mark it `historical`, in a commit that changes only the status, and tell the new outcome in a new report. A report is never promoted; an arc over several experiments is a new report or an entry.

## Example

```html
<meta name="title" content="The error of the pi estimate fell as 1/sqrt(n), but tight per-size predictions missed">
<meta name="description" content="The RMS error of a Monte Carlo estimate of pi, at five sample sizes from 64 to 16,384 points.">
<!-- body -->
<h2 id="happened">What happened</h2>
<p>The RMS error fell with a fitted log-log slope of -0.493 (<a href="/content/results/R-2.md">R-2</a>), against -0.5 in theory. The protocol's first rule kept the hypothesis.</p>
<p>An earlier result, <a href="/content/results/R-1.md">R-1</a>, since superseded, fitted the slope to the mean absolute error where the protocol names the RMS error.</p>
<h2 id="not">What this does not show</h2>
<ul>
  <li>Anything about another estimator or another random generator.</li>
  <li>Any sample size outside 64 to 16,384 points.</li>
</ul>
```
