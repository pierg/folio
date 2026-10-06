# Code

**When.** The exact text matters: a function as written, a configuration as committed, a command as run. If only the idea matters, it is prose with `<code>` spans.

## A listing

`<pre><code>`, verbatim. The shell gives it a sunk box and a sideways scroll, so a long line never widens the page. Keep to what the reader needs: cut with a `…` line, and say what was cut.

```html
<pre><code># folio.yaml: the checks the gate runs as errors
checks:
  uncited-number: error
</code></pre>
```

## A walkthrough

When the reader should follow code line by line, give each line its own element, mark the one under discussion, and let a stepper move the mark. The page's own classes carry it:

```html
<div class="kx-code" data-step="2">
<div class="kx-line" data-n="1">for doc in library.documents:</div>
<div class="kx-line" data-n="2">    for problem in check(doc):</div>
<div class="kx-line" data-n="3">        report(problem)</div>
</div>
```

A rule such as `.kx-code[data-step="2"] [data-n="2"] { background: var(--accent-soft); }` marks the line, and the script only changes `data-step`.

## Before and after

Two listings in `.cols`: a `lane-baseline` lane, then a `lane-kept` lane. A unified diff in one `<pre>` is fine when the change is small and the reader knows diffs; two lanes are better when the change is a restructure.

## Commands and output

The command in one `<pre>`, its output in another, never mixed into prose. Show the exit code when it matters.

## Do not

- Screenshot code.
- Load a highlighting library. The shell has none, and pages stay free of dependencies; a marked line carries the emphasis.
- Paste a whole file when three lines carry the point.
