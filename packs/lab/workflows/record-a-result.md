---
name: record-a-result
pack: lab
summary: Record one measured number as a result, tied to the locked protocol it came from.
inputs:
  - protocol: the slug of the protocol the run followed
  - number: the value with its denominator, exactly as rederive prints it
  - baseline: what it is compared against, on the same inputs
  - bound: where the number holds and where it says nothing
  - evidence: the path of the raw measurement, from the charter's root
  - rederive: the command that prints the number from the evidence
  - title: (optional) a plain sentence carrying the number; drafted from the fields if not given
  - description: (optional) one line on what was measured and against what; drafted if not given
  - date: (optional) the day it was recorded; default today
  - supersedes: (optional) the id of the result this one corrects
  - tags: (optional) tags for the result
  - from: (optional) a YAML file holding any of these fields, with #<key> for one entry in it
produces: [result, journal-entry]
---

# Record a result

You bring a number, its evidence and the protocol it came from; you get a result with the next free id, shown on its protocol's page and logged in the journal.

This workflow records. It does not decide whether the result counts. When lab-kit runs the lab, its review decides that before this workflow starts. Without lab-kit, the owner decides, and step 1 asks.

Every field of the result is an input. Take what the request gives, then what the `from` file gives; a value in the request wins. Ask, in one message, only for required fields still missing.

## Steps

1. **Confirm the number may be recorded.** Without lab-kit, ask the owner. The request itself counts as a yes when it says so plainly.
2. **Read the protocol.** Run `folio cite <slug>` for its path, then read it. Its status must be `locked`. Find the measure this number reports.
3. **Re-derive the number.** Run the `rederive` command yourself, from the charter's `root`. Compare what it prints with the number you were given. The result's `number` is exactly what the command printed, never a value from a summary.
4. **Check the evidence.** The evidence path exists, resolved from the charter's `root`, and is in the repository, not only on this machine.
5. **Look for an earlier result.** Run `folio search` with the measure's words. If a live result reports the same measure under the same conditions, this one supersedes it.
6. **Write the result.** Through the write skill, which runs `folio new result` for the next free id. Fill every field, `date` included. Write the bound beside the number.
7. **Name what it supersedes.** If it replaces an earlier result, the write skill sets `supersedes` on the new one. The old file is never opened: the engine marks it `superseded` and shows a banner on it. No list needs a line for the new result either: its protocol's page shows it.
8. **Log it.** Through the write skill, which runs `folio journal add --title "Recorded <id>" --description "<the result's title>" --body ".." --about <id>,<protocol>`. The body links the evidence and says, in a sentence, what the number changes.
9. **Run the gate.** `folio index`, then `folio check` passes. If `cites-superseded` now names pages, list them for the owner.
10. **Commit.** Add exactly: the result, the journal entry, `.folio/`, the evidence the result names, and every script and input its `rederive` command reads, if they are not committed yet. A command that cannot run from a fresh clone re-derives nothing. Never `git add -A`. The result is permanent from this commit on.

## Stops

- The owner has not said the number may be recorded.
- The protocol is `draft` or `abandoned`. A result never comes from a plan that was not locked first. Results recorded before a protocol was abandoned stay valid.
- The protocol names no measure that matches this number. Ask whether it belongs to this protocol at all.
- The command fails, or prints a different number. Report both values, and record nothing.
- The evidence is missing, or exists only outside the repository.
- It is unclear whether this result supersedes an earlier one. Ask.

## Done when

- The result exists with every field filled, its protocol locked, its evidence present.
- The number in it is the one the command printed.
- Its protocol's page shows it, and the journal has one entry about it.
- Any result it replaces is named in its `supersedes` field, and no older file was edited.
- `folio check` passes, and the owner has the list of pages that still cite a superseded result.
- The result and its evidence are committed.
