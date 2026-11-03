---
name: claim
pack: lab
format: markdown
path: content/claims/C-{n}.md
id: prefix:C
skeleton: skeleton.md
lives: revised
states: [draft, live, withdrawn]
fields:
  - { name: strength, type: enum, values: [indicative, supported, general], required: true }
checks:
  require: [claim, licensed-by, bounds, must-not]
  cites: results
  max_words: 250
on_map: optional
---

# Claim

A claim is one thing the lab may say, at a stated strength, with the results behind it and what must not be said beside it.

## Reader

Anyone about to write a sentence about the work in a report, a paper or a talk. They want to know how far they can go, and where they must stop.

## Voice

Careful and graded. The claim is one sentence, no stronger than its weakest result allows. The limits are stated as plainly as the claim.

> From 64 to 16,384 points, the RMS error of this Monte Carlo estimate of pi falls as one over the square root of the number of points.

## Metadata

Front matter holds `title` (the claim, shortened), `description`, `genre`, `id`, `status`, `tags`, and this field:

- `strength` (required): one of three words.
  - `indicative`: one setting, or few runs. Worth saying, with its conditions.
  - `supported`: repeated runs in one setting, consistent.
  - `general`: holds across every setting its bounds name.

The shell shows the strength beside the title and filters claims by it. The `description` says in one line where the claim stops.

## Shape

The shell draws the title, the description, the status and the strength above the body. The body, as `##` sections in this order:

1. `## Claim` (`claim`): the claim, in one sentence.
2. `## Licensed by` (`licensed-by`): a list of the results it rests on, each cited by id, with one line on what it adds.
3. `## Bounds that travel with it` (`bounds`): the conditions any sentence using this claim must carry.
4. `## Must not be said` (`must-not`): the nearby sentences the results do not license, each with why.

## Forbidden

- A claim that cites no result. Caught by `cites: results`.
- A strength word outside the three. Caught by `fields`, through the `enum` type.
- A claim stronger than its weakest result. Judged, not checked.
- A number restated as the claim's own. Caught by `uncited-number` when the number cites nothing; otherwise judged, not checked. Cite the result instead.
- A claim resting on a superseded result. Caught by `cites-superseded`.

## Steps

- Read every result it will cite, including their bounds. The claim's bounds include all of theirs.
- Give it the next free id with `folio new claim`.
- Fill "Must not be said" with the sentences a hurried reader would write next. That section does as much work as the claim.
- Who sets the strength is the owner's call, or lab-kit's. folio checks only that the word is one of the three.

## Lifecycle

Revised deliberately: when a new result widens, narrows or breaks it. Each revision gets a journal entry saying what changed and which result moved it. A claim the results no longer support becomes `withdrawn`, and says why in its claim section. Its id is never reused.

## Example

```markdown
---
title: The pi estimator's error falls at the 1/sqrt(n) rate
description: Only for this estimator and generator, from 64 to 16,384 points.
genre: claim
id: C-1
strength: indicative
tags: [monte-carlo, convergence]
---

## Claim

From 64 to 16,384 points, the RMS error of the lab's Monte Carlo estimate of pi falls as one over the square root of the number of points (`R-2`).

## Licensed by

- `R-2`: the fitted log-log slope of the RMS error, -0.493, from one locked run.

## Bounds that travel with it

One estimator, Python's standard generator, and five sample sizes from 64 to 16,384 points. One run of 100 seeds per size.

## Must not be said

- "Every Monte Carlo estimate converges at this rate." Only this estimator was run.
- "The estimate is unbiased." No result measures the bias.
```
