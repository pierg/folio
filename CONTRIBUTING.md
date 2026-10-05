# Contributing

## Run the tests

```bash
pip install -e ".[dev]"
python -m pytest -q
(cd docs && folio check)
(cd docs && folio serve)   # read the documentation at http://127.0.0.1:5170/
```

Tests that compile a paper skip with a reason when `latexmk` is not installed.

## How a change lands

1. Open an issue or a pull request that says what changes and why, in a few lines.
2. Change the specification first when behaviour changes: `docs/spec/` says what folio does, and the code, genre cards, packs and skills follow it. A change to a check names it in `docs/spec/checks.md` in the same pull request.
3. Add or update tests beside the change.
4. Run the tests and the documentation gate above. Both must pass, as they do in CI.
5. If the change is worth a dated record, add a journal entry to the documentation library through the write skill (`folio journal add`, run from `docs/`).

## The specs win

When the code, a genre card, a skill or a documentation page disagrees with `docs/spec/`, the spec is right and the other is fixed. If the spec itself is wrong, change it in the same pull request, and say so.

## Writing

Plain words and short sentences, one idea per sentence. No em-dashes. Examples are generic or about folio itself.
