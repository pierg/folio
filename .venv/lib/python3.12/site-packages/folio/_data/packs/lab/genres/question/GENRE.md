---
name: question
pack: lab
format: markdown
path: content/questions/Q-{n}.md
id: prefix:Q
skeleton: skeleton.md
lives: revised
states: [draft, live, narrowed, answered, dropped]
fields:
  - { name: rank, type: integer, required: true }
checks:
  require: [why, settle, drop, answer]
  answer_cites: [result, claim]
on_map: required
---

# Question

A question is one open research question, ranked against the others, with what would settle it and what would make you drop it.

## Reader

Anyone choosing what to work on next, and anyone asking why an experiment was run. They know the field. They want the question exact enough to test.

## Voice

Precise and falsifiable. The title is the question itself, ending in a question mark. Each section says something a measurement could contradict.

> Does the error of a Monte Carlo estimate of pi shrink as 1/sqrt(n)?

## Metadata

Front matter holds `title` (the question), `description`, `genre`, `id`, `status`, `tags`, and this field:

- `rank` (required): a positive whole number; 1 is the most important open question. The shell sorts questions by it.

The `description` says in one line what the answer would change.

## Shape

The shell draws the question, the description, the status and the rank above the body. A generated panel lists the protocols whose `question` field names it, and each protocol's page lists its results. Nobody keeps that list by hand.

The body, as `##` sections in this order:

1. `## Why it matters` (`why`): what changes for the work once the answer is known.
2. `## What would settle it` (`settle`): the observation that would answer it, either way.
3. `## What would make us drop it` (`drop`): the outcome or cost that ends this line of work without an answer.
4. `## Answer` (`answer`): empty while the question is open. Once narrowed or answered, one or two sentences citing the results and claims that narrow or settle it.

## Forbidden

- A question nothing could answer. Judged, not checked; if no measurement could settle it, it is a direction, and belongs on a map.
- Two questions in one. Judged, not checked; split it, one id each.
- An answer that cites nothing. Caught by `answer_cites` when the status is `answered` or `narrowed`.
- A hand-written list of the protocols and results about it. Judged, not checked; the generated panel holds it.
- An id reused or renumbered. Caught by `unique-id`.

## Steps

- Search the library first (`folio search`). Sharpen an existing question rather than open a near-duplicate.
- Give it the next free id with `folio new question`. Never pick a number by hand.
- Set the rank against the other `live` questions, and re-rank them in the same change if needed.

## Lifecycle

Revised in place: the wording sharpens and the rank moves. It is `live` while open, from its first commit: fill why, settle and drop before then. Hold it as `draft` only when the owner asks.

When results settle part of it but leave it open, the status becomes `narrowed`. The wording sharpens to what is left. The answer section says which part was settled, citing the results. When the results settle it, the status becomes `answered` and the answer section cites them. When the drop condition is met, the status becomes `dropped`, and the answer section says which outcome dropped it. An answered or dropped question stays in the library, marked. Who decides that a question is answered is the owner's call, or lab-kit's; folio checks only that the answer cites something.

## Example

```markdown
---
title: "Does the error of a Monte Carlo estimate of pi shrink as 1/sqrt(n)?"
description: The answer says how many samples a given accuracy costs.
genre: question
id: Q-1
rank: 1
tags: [monte-carlo, convergence]
---

## Why it matters

Each point drawn either lands inside the quarter circle or not, so the estimate is a scaled average of independent yes-or-no draws. Theory says its error then shrinks as one over the square root of the sample size. If it does, the cost of any accuracy can be read off one line.

## What would settle it

The root mean square error of the estimate over many seeds, at sample sizes spread over several powers of two, fitted on a log-log scale. A slope near -0.5 answers yes; a slope clearly steeper or shallower answers no.

## What would make us drop it

An error that does not shrink at all as the sample grows: then the sampler or the estimator is broken, and no slope means anything.

## Answer
```
