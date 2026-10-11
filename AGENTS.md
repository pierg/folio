# AGENTS.md: working on folio itself

This file is for agents changing folio's engine, genres, packs, skills or documentation. `CLAUDE.md` is the one line `@AGENTS.md`.

## Read first

1. `README.md`: what folio is and how it installs.
2. `docs/spec/model.md`: the contract. Then `checks.md`, `commands.md`, `genre-format.md`, `pack-format.md` and `skill-format.md` in `docs/spec/` as the change needs.
3. `CONTRIBUTING.md`: how a change lands.

## Layout

- `src/folio/`: the engine and the `folio` command. `src/folio/checks/` holds the gate.
- `genres/`, `packs/`, `skills/`, `shell/`, `craft/`: data shipped inside the package (see `pyproject.toml`).
- `tests/`: pytest. `tests/fixtures/sample/` is a small library with every genre.
- `docs/`: folio's documentation, itself a folio library. Change it through the skills, as any library: `.agents/skills` links to `skills/`.
- `docs/spec/`: the specification, Markdown outside the library's `content/`.

## The gate

```bash
python -m pytest -q
cd docs && folio check
```

Both must pass before a change is done, and CI runs the same two commands. After `pip install -e ".[dev]"`, `folio` is this checkout's engine.

## Rules

- The specs win. Change `docs/spec/` first when behaviour changes, and the code, cards, packs and skills to match, in the same change.
- A check is added to the engine and to `docs/spec/checks.md` together. A card or pack uses only listed check names.
- Every `folio` command and flag named in a skill, card, spec or `SETUP.md` must exist; `tests/test_docs_commands.py` checks this.
- Fail loud: an error names what is wrong and where. No silent fallbacks.
- Use `FOLIO_TODAY` in tests for dates.
- Plain words, short sentences, no em-dashes. Examples are generic or about folio itself.

## Frozen surfaces

- In `docs/`, a committed journal entry, a committed result and a locked protocol are never edited: the gate checks them against git. Correct them with a new document that points back.
- The generated indices in `docs/.folio/` and `tests/fixtures/sample/.folio/` are written by `folio index`, never by hand.
- `.agents/skills` is a link to `skills/`. Edit the skill bodies in `skills/`.

<!-- ops:lanes:start (generated from the owner's central rules; change them there, not here) -->
## How changes reach main

`main` is the only source of truth and is always clean: every commit on it passes the gate below.
Pull before you start; never leave work only on a machine.

**Content lane.** Content here means reader comments recorded by the folio server, and pages in the `docs/` library.
Commit content straight to `main`: pull, change only content, run the gate, commit, push. If the
push is refused because `main` moved, pull with rebase and push again.

**Change lane.** Everything else (code, scripts, configuration, schemas, skills, this file, CI,
dependencies) goes through a pull request:
1. Branch from the latest `origin/main` in a separate worktree, named after the task (its tracker
   issue, for example `pie-142-fix-login`).
2. Push early and open a draft pull request.
3. When the work is done and the gate passes, squash-merge it with a clear title and description,
   then delete the branch and the worktree.

If a change mixes both, it takes the change lane.

**Gate:** `python -m pytest -q`, then `cd docs && folio check`.

**Authorship.** Every commit is authored with the repository owner's git identity. No co-author
line, tool or agent name, "generated with" footer or session link appears in a commit message, a
branch name or a pull request. A check on every push and pull request enforces it.
<!-- ops:lanes:end -->
