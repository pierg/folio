---
title: Time folio check on two libraries
description: Varies the library checked, and measures the wall-clock time of folio check.
genre: protocol
status: locked
question: Q-1
tags: [gate, timing]
---

## Hypothesis

`folio check` on this documentation library has a median wall-clock time under two seconds over ten runs.

## Intuition

The gate reads every document once, resolves links against an in-memory catalog, and asks git about the few files with a lifecycle. A library of a few dozen documents should take about as long as starting Python and git. If it fails, the cost will come from reading git history or from rebuilding the indices to compare them.

## The one variable

The library checked. Arms: `sample`, the small library the test suite uses (`tests/fixtures/sample`), and `docs`, this documentation library.

## Held fixed

One machine, one Python, one engine version, both libraries in one working tree, run one after the other. One untimed warm-up run before each arm. The gate must pass on every timed run; a run that fails records nothing.

## Pinned configuration

```yaml
engine: folio 0.1.0, installed from this repository
python: "3.11"
command: python -m folio check
script: docs/tools/check_timing.py
runs_per_arm: 10
warm_up_runs: 1
evidence: docs/assets/data/check-timings.csv
budget: none (no network, no model calls)
```

## Allowed moves

Nothing under test makes moves: the gate is fixed code and changes no file.

## Measures

Wall-clock seconds per run of `folio check`, from process start to exit, measured by `check_timing.py` with `time.perf_counter`. Per arm, the median of ten runs. The script also records the number of documents the gate reports, to state the library's size beside the time.

## Decision rules

- D1: keep the hypothesis if the `docs` arm's median is under two seconds.
- D2: drop it if the `docs` arm's median is two seconds or more.
- D3 (kill): if any arm's slowest run is more than three times its fastest, the timings are too noisy on this machine; stop and find a quieter one before recording anything.

## Predictions

- P1: the `docs` arm's median is under two seconds. Confidence: 85%.
- P2: the `docs` arm's median is higher than the `sample` arm's. Confidence: 70%.

## What it cannot show

How the time grows with library size beyond these two libraries, how it behaves on another machine or operating system, or how long the gate takes once the library has a long git history to read.
