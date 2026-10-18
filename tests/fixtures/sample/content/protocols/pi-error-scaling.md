---
title: How the error of the pi estimate scales with the sample size
description: The number of points is varied; the RMS error over 100 seeds is measured.
genre: protocol
status: locked
question: Q-1
---

## Hypothesis

The RMS error of the estimate falls as one over the square root of the number of points.

## Intuition

Each point is an independent draw, inside the quarter circle or not.

## The one variable

The number of points: 64, 256, 1,024, 4,096 and 16,384.

## Held fixed

The estimator, the random generator and the seeds.

## Pinned configuration

```yaml
sizes: [64, 256, 1024, 4096, 16384]
repeats: 100
```

## Allowed moves

Nothing under test makes moves.

## Measures

The RMS error over 100 seeds, per size, and the log-log slope across sizes.

## Decision rules

- D1: a slope between -0.6 and -0.4 keeps the hypothesis.
- D2 (kill): an error that does not shrink drops it.

## Predictions

- P1: the slope lies between -0.55 and -0.45. Confidence: 85%.

## What it cannot show

Anything about another estimator.
