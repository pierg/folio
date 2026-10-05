---
title: "{{What this experiment tests, in one line}}"
description: "{{One line: what is varied and what is measured}}"
genre: {genre}
status: draft
question: "{{Q-n}}"
tags: ["{{tags}}"]
---

## Hypothesis

{{One falsifiable sentence.}}

## Intuition

{{In plain words: why it should work, and what failure would look like.}}

## The one variable

{{The single thing varied, in one sentence, and the arms: the values it takes.}}

## Held fixed

{{Everything else that could move the measures, each at a stated value.}}

## Pinned configuration

```yaml
{{every model, tool, setting, image digest and budget a run uses}}
```

## Allowed moves

- {{Every move the agent or procedure under test may make, or one line saying nothing under test makes moves.}}

## Measures

{{Each measure: what is counted, its unit and denominator, and how.}}

## Decision rules

- D1: {{An outcome and what it decides: keep, drop or inconclusive.}}
- D2 (kill): {{The outcome that ends this line of work.}}

## Predictions

- P1: {{A prediction that can be scored hit or miss.}} Confidence: {{n}}%.

## What it cannot show

{{What no outcome of this experiment would tell you.}}
