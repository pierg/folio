---
name: write-a-report
pack: lab
summary: Write the plain-English report of one experiment, frozen once published.
inputs:
  - results: the ids of the results the report tells
  - map: the map it belongs on
  - slug: (optional) the report's slug; `<protocol-slug>-report` if not given
  - title: (optional) the outcome, in one plain line
  - description: (optional) one line on what was tested, and on what
  - question: (optional) the question it serves; read from the protocol if not given
  - intuition: (optional) the protocol's intuition, in plain words; read from the protocol if not given
  - run: (optional) what was run, including any voided run or re-run
  - scoring: (optional) how each decision rule and prediction came out, by id, if already on record
  - lesson: (optional) why it did or did not work
  - bounds: (optional) every bound and what was not measured; read from the results if not given
  - from: (optional) a YAML file holding any of these inputs, with #<key> for one entry in it
produces: [report, map-row, journal-entry]
---

# Write a report

You name the results of one experiment; you get a report a newcomer can read, frozen once published, with its misses told as plainly as its hits.

The report tells the outcome, and it is where a protocol is scored: "What we expected" states the predictions and decision rules as locked, and "What happened" says how each came out, by id. When lab-kit runs the lab, its review scores them first and the report states that scoring. Without lab-kit, you score against the locked protocol here, and the owner confirms it before the report is published.

Take every input the request or the `from` file gives. Read the rest from the results, their protocol and the journal. Ask, in one message, only for what is still missing.

## Steps

1. **Read the results.** Read each result named. Every one must be `live`: run `folio cite <id>` for its derived status.
2. **Read what they came from.** Read the protocol each result names, and the question that protocol addresses.
3. **Read what may be said.** Find the claims that cite these results: the page panel's "what links here", or `folio search` with each id. Note their bounds and their "Must not be said".
4. **Read the record of the run.** Unless the inputs give them, read the journal entries about this experiment for what was run and the lesson. Find any scoring of the decision rules and predictions already on record.
5. **Write the report.** Through the write skill, which runs `folio new report <protocol-slug>-report --status draft`: a report is frozen once `live`, so it is held as a draft until published. Fill the sections in order. Write "What we expected" from the protocol, as it stood before the run.
6. **Cite every number.** Run `folio cite <id>` for each result's link markup. Every measured number sits beside the link to its result.
7. **Score it, and give the nulls their place.** In "What happened", mark each decision rule and each prediction hit or miss, by id, exactly against the locked protocol. Each miss and each null gets the same plainness as each hit. Every bound the results carry goes in "What this does not show".
8. **Reuse the figures.** Take figures from `assets/figures/`. If a figure the report needs does not exist, make it there, so a paper can reuse it.
9. **Put it on a map.** Run `folio map add <map> <report> [--group "<heading>"] [--after <doc>]`. Add `--reason "..."` only when one line on why to follow it says more than the report's description.
10. **Publish it.** Set the status to `live`. Write no list of links: the generated panels show what it cites.
11. **Log it.** Through the write skill, which runs `folio journal add --title "Reported <the report's title>" --description ".." --body ".." --about <report>,<result ids>`. The body says in a sentence what the report concludes.
12. **Run the gate.** `folio index`, then `folio check` passes.
13. **Commit.** Add exactly: the report, its annotation file if any, the map, the journal entry, `.folio/`, and any figure made in `assets/figures/`. Never `git add -A`. From this commit on the report is frozen and never rewritten.

## Stops

- A result is `superseded` or `retracted`. Ask whether to report the replacement instead.
- The report needs a number no result holds. Record it first with record-a-result, or leave it out.
- The owner has not confirmed the scoring, when lab-kit is not running the lab. Show it and ask before publishing.
- A sentence the story needs is one a claim says must not be said. Ask before writing it.
- No map fits, and the request names none. Ask which map.

## Done when

- The report has every section, in order, and its status is `live`.
- Every measured number cites a live result.
- Nulls and misses are stated as plainly as wins, and every bound appears in "What this does not show".
- The report is on a map, and the journal has one entry about it.
- `folio check` passes, and the report is committed.
