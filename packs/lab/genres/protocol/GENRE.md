---
name: protocol
pack: lab
format: markdown
path: content/protocols/{slug}.md
id: slug
skeleton: skeleton.md
lives: frozen
states: [draft, locked, abandoned]
frozen_in: [locked]
frozen_exits: [abandoned]
fields:
  - { name: question, type: id, genre: question, required: true }
  - { name: amends, type: id, genre: protocol }
  - { name: carries, type: id, genre: protocol }
checks:
  require: [hypothesis, intuition, variable, fixed, configuration, moves, measures, rules, predictions, limits]
  prediction_ids: true
  rule_ids: true
  pinned_config: true
on_map: optional
---

# Protocol

A protocol is the plan for one experiment, written before it runs: the hypothesis, the one variable, the measures, the rules that decide, and the predictions.

## Reader

Whoever runs the experiment, and whoever later asks whether its result means what it seems to. They need the plan exact enough that two people would run the same experiment and score it the same way.

## Voice

Exact and testable. Every sentence is a commitment that the run could break. No "we will explore" and no "roughly". The intuition is the one place for plain, informal words.

> D1: keep the hypothesis if the fitted log-log slope of the RMS error lies between -0.6 and -0.4.

## Metadata

Front matter holds `title`, `description`, `genre`, `status`, `tags`, and these fields:

- `question` (required): the id of the question it addresses, such as `Q-1`. The question's page lists this protocol in a generated panel.
- `amends` (optional): the slug of an earlier locked protocol this one corrects.
- `carries` (optional): the slug of an earlier protocol whose mechanics this one copies: its scripts, its pins, its setup.

The `description` says in one line what is varied and what is measured.

## Shape

The shell draws the title, the description, the status and the fields above the body. A generated panel lists the results whose `protocol` field names it.

The body, as `##` sections in this order:

1. `## Hypothesis` (`hypothesis`): one falsifiable sentence.
2. `## Intuition` (`intuition`): in plain words, why it should work, and what failure would look like.
3. `## The one variable` (`variable`): the single thing varied, in one sentence, and the arms: the values it takes.
4. `## Held fixed` (`fixed`): everything else that could move the measures, each at a stated value.
5. `## Pinned configuration` (`configuration`): one fenced `yaml` block. It pins every model, tool, setting, image digest and budget a run uses. A run must use exactly this configuration.
6. `## Allowed moves` (`moves`): a list of every move the agent or procedure under test may make. A move the list does not name is one it may never use. When nothing under test makes moves, the section says so in one line.
7. `## Measures` (`measures`): each measure, what is counted, its unit and its denominator, and how it is counted.
8. `## Decision rules` (`rules`): a list. Each item opens with its id, `D1:`, `D2:` and so on. Together they say which outcomes keep the hypothesis, which drop it, and which are inconclusive. Exactly one item is the kill rule, marked `(kill)` after its id: the outcome that ends this line of work.
9. `## Predictions` (`predictions`): a list. Each item opens with its id, `P1:`, `P2:` and so on, can be scored hit or miss, and ends in `Confidence: <n>%`.
10. `## What it cannot show` (`limits`): what no outcome of this experiment would tell you.

The ids `P1`, `D1` are stable. A score, a result and a report refer to a prediction or a rule by them.

## Forbidden

- Two things varied at once. Judged, not checked; split it into two protocols.
- A prediction or a rule without its id, ids out of order, or no kill rule. Caught by `prediction_ids` and `rule_ids`.
- A prediction with no confidence. Caught by `prediction_ids`.
- A configuration that is not one parseable `yaml` block. Caught by `pinned_config`. Whether it pins everything is judged, not checked.
- A decision rule that leaves an outcome unscored. Judged, not checked.
- A placeholder left in any section. Caught by `placeholder`.
- An edit after the lock. Caught by `frozen`: the file matches the first commit that locked it, and its status may then move only to `abandoned`.

## Steps

- Write the decision rules and the predictions before anyone sees a number. That is the point of the genre.
- Name each measure exactly as the result will report it, so the result can cite this protocol without translation.
- Number predictions and rules from 1, without gaps. Once the protocol is locked, the ids never change.
- Lock it before any run: set `status: locked`, run `folio index` and `folio check`, and commit. Without a tool built on folio, also add a journal entry of kind `lock` about it. The lock commit is the protocol's anchor.
- No list needs a line for it. Its `question` field puts it on the question's page.

## Lifecycle

Frozen. `draft` while it is being written, revised freely. `locked` once committed with that status, and never edited from then on; the gate checks the bytes against the lock commit (check `frozen`). The lock is recorded in the journal with an entry of kind `lock` about the protocol: lab-kit writes it where it runs the lab, and the write skill otherwise.

A mistake found after the lock is not fixed in place. A new protocol names the old one in `amends` and says what changed. A journal entry of kind `correction` about the old protocol says why, and shows on it as a banner. A protocol that will never run becomes `abandoned`, before or after its lock, with a journal entry saying why. After the lock that is the only status change allowed, in a commit that changes nothing else.

## Example

````markdown
---
title: How the error of the pi estimate scales with the sample size
description: Varies the number of points drawn, and measures the root mean square error over 100 seeds.
genre: protocol
status: locked
question: Q-1
tags: [monte-carlo, convergence]
---

## Hypothesis

The root mean square error of the estimate falls as n to the power -0.5, where n is the number of points drawn.

## Intuition

Each point is an independent yes or no: inside the quarter circle with probability pi/4. The estimate is four times the share of yeses, so its spread should shrink as one over sqrt(n), a line of slope -0.5 on a log-log plot. If it fails, it will be because the points are not independent enough, or the estimator is biased, so that the error stops falling.

## The one variable

The number of points drawn per estimate. Arms: 64, 256, 1,024, 4,096 and 16,384 points, each four times the last.

## Held fixed

The estimator in `substrate/estimator.py`. Python's standard generator, seeded per estimate. 100 estimates per arm, each with its own seed. The true value is `math.pi`.

## Pinned configuration

```yaml
language: python 3, standard library only
substrate: substrate/estimator.py
generator: random.Random, one per estimate
sizes: [64, 256, 1024, 4096, 16384]
repeats: 100
seed: size * 1000 + repeat
truth: math.pi
budget: none (token-free)
```

## Allowed moves

Nothing under test makes moves: the estimator is fixed code.

## Measures

- The RMS error of an arm: the square root of the mean squared error over its 100 estimates.
- The slope: the least-squares slope of ln(RMS error) against ln(n) over the five arms, printed to three decimals.

## Decision rules

- D1: keep the hypothesis if the slope lies between -0.6 and -0.4.
- D2: drop it if the slope is below -0.7 or above -0.3. Between the D1 and D2 bands is inconclusive.
- D3 (kill): if the RMS error at 16,384 points is not below the RMS error at 64 points, stop this line: the sampler or the estimator is broken.

## Predictions

- P1: the slope lies between -0.55 and -0.45. Confidence: 85%.
- P2: the RMS error at 16,384 points is below 0.015. Confidence: 90%.

## What it cannot show

Anything about another estimator, another generator, or sample sizes outside 64 to 16,384. Running time was not measured.
````
