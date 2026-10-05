---
name: quiz
pack: knowledge-base
summary: Ask the reader the flashcards in one part of the library, grade each answer, and record what stuck in one journal entry.
inputs:
  - scope: a map, a tag, or one document
  - count: how many cards to ask (default 10)
produces: [journal-entry]
---

# Quiz

You name a part of the library; you are asked its flashcards one at a time, told how each answer did, and the journal records what stuck.

A flashcard is a component inside any HTML page, not a genre: `<details class="card"><summary>question</summary>answer</details>`. The summary is the question. The rest is the answer. `folio cards` lists them, read from the files as they are now. A check-yourself block (`<details class="check">`) is not a flashcard, and the quiz never asks it: it tests its own section, where the reader meets it.

## Steps

1. **Pick the scope.** If the request names none, list the maps with `folio maps`, count each one's cards with `folio cards --map <map> --json`, and ask the reader to choose.
2. **Gather the cards.** Run `folio cards --map <map> --json`, `--tag <tag>` or `--doc <doc>` for the scope. Each card comes with its question, its answer and its page.
3. **Choose the order.** Read the earlier `lesson` entries for this scope: `folio journal --kind lesson --about <map or doc>`, or `--tag <tag>`. Ask first the cards missed last time, then cards never asked, then the ones asked longest ago. Stop at the count.
4. **Ask one card at a time.** Show the question only. Wait for the answer. Never show the answer first, never ask two at once, and never hint.
5. **Grade each answer against the card.**
   - *Got it*: the substance is there, in any words.
   - *Partly*: say in one sentence what was missing.
   - *Missed*: give the answer in one or two sentences, and the page to reread.
   Do not soften a miss. Do not grade beyond what the card and its page say.
6. **Set aside a bad card.** If a card's answer looks wrong, unclear or out of date, do not grade against it. Say why, and note it for the record.
7. **Record what stuck.** Through the write skill, which runs `folio journal add --kind lesson --title "Quiz: <scope>, <got> of <asked>" --description "<one line on what stuck and what did not>" --body ".." --about <map or doc>`. For a tag scope, pass `--tags <tag>` instead of `--about`. The body lists the cards by their question, in three groups: stuck, partly, missed. Missed cards name the page to reread. Set-aside cards are listed with the reason. Keep the body under 150 words: name the cards briefly, and never copy their answers.
8. **Run the gate.** `folio index`, then `folio check` passes.
9. **Commit.** Add exactly the new journal entry, any card fixed at the reader's request, and `.folio/`. Never `git add -A`.

## Stops

- The scope holds no cards. Say so, and ask whether to add cards through the write skill, or pick another scope.
- The reader asks to stop. Record the cards asked so far, then stop.
- A card's answer contradicts its page. Ask whether to fix the card now through the write skill, or leave it for later.

## Done when

- Every card asked has a grade, and every set-aside card has a reason.
- The quiz ends with one journal entry of kind `lesson`, under 150 words, about its scope.
- No document changed, unless the reader asked for a card to be fixed. The journal entry is the only new file.
- `folio check` passes.
