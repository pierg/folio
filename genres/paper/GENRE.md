---
name: paper
format: latex
path: content/papers/{slug}/main.tex
id: slug
skeleton: skeleton.tex
lives: revised
states: [draft, live, historical, retired]
checks:
  require: [abstract, bibliography]
  cites: any
  bib: assets/refs.bib
  figures: assets/figures
on_map: required
parts:
  landing:
    path: content/papers/{slug}/index.html
    skeleton: skeleton-landing.html
    address: true
    checks: {}
  version:
    path: content/papers/{slug}/versions/{name}/main.tex
    lives: permanent
    on_map: never
    checks: {}
---

# Paper

A paper is a LaTeX article for a venue: it cites the library's documents by id and takes figures and references from the shared assets.

A paper has a source, a landing page and its versions, all of this genre. The **source** is `main.tex` in the paper's folder, and it is revised for as long as the paper lives. The **landing page** is the `landing` part, `index.html` beside it, and links to the paper land there. It carries the paper's metadata and frames it for a reader deciding whether to open the PDF. A **version** is a snapshot: `folio paper freeze` copies the source and its built PDF into `versions/<name>/`, and that folder is never edited again. The abstract has one home, `main.tex`: `folio index` reads it from there, and the shell shows it on the landing page. The figures come from `assets/figures/` and the references from `assets/refs.bib`. Neither is copied into the paper's folder.

## Reader

Source: a reviewer or a reader in the field, who knows the area and reads critically. Landing page: someone deciding whether the paper is worth opening.

## Voice

Scholarly. Precise, measured, and claims no more than its evidence. "We" for the authors. Each term is defined on first use or cited. It follows the venue's conventions. A library with a second venue style adds a variant, such as `paper-workshop`, rather than changing this voice.

> We show that tiled attention matches the reference output at every sequence length we tested, and that its memory grows linearly with the length.

## Metadata

The metadata lives in the landing page's `<meta>` tags. `main.tex` holds only what LaTeX needs to typeset the paper, such as `\title`. `folio new paper <slug> --title ".."` writes the title into both, so they start the same; keep them the same when you revise it.

- The `title` is the paper's title. The `description` says in one sentence what the paper shows.
- The shell draws the title, description and status on the landing page, then the abstract from `main.tex`, a link to the current PDF when one is built, and the list of versions with their PDFs and dates. All of it comes from the indices and the build, never from the page.

## Shape

The source, `main.tex`:

1. A preamble that loads `graphicx` and `hyperref`, sets `\graphicspath` to the library's `assets/figures/`, and loads `folio` (`folio.sty`, which the build provides and which makes `\fcite` a link).
2. `\title`, `\author`, then `abstract`: one `abstract` environment.
3. Sections, in the venue's order.
4. Citations. `\fcite{<id>}` cites a document of this library by its id, such as a concept, an entry or a result. `\cite{<key>}` cites an outside work from `assets/refs.bib`.
5. Figures, each `\includegraphics` naming a file from `assets/figures/`.
6. `bibliography`: `\bibliography` pointing at `assets/refs.bib`.

The landing page, `index.html`, holds only framing, and it is optional: a paragraph or two for a reader deciding whether to open the PDF. The venue, and who the paper is for. The shell draws everything else.

A version, `versions/<name>/`, holds `main.tex` and `paper.pdf` exactly as `folio paper freeze` wrote them. Nobody writes one by hand.

## Forbidden

- A `\fcite` that does not resolve to a document id. Caught by `broken-link`, and the build fails on it.
- A `\cite` key missing from `assets/refs.bib`, or a bibliography file of the paper's own. Caught by `bib`.
- A figure from anywhere but `assets/figures/`. Caught by `figures`.
- Any change to a committed version's folder. Caught by `permanent`.
- An abstract, a status, a PDF link, a list of versions or a list of cited documents written on the landing page. The shell draws them. Judged, not checked.
- A fact restated by value where its home could be cited. Judged, not checked; with the lab pack on, an uncited number is caught by its rule.
- Sentences copied from a sibling document, such as a report or an entry on the same result. Siblings share ids and figures, never sentences. Judged, not checked.

## Steps

- Find a document's id and citation markup with `folio cite <id>`.
- Make a figure once, in `assets/figures/`, so the pages and the paper show the same one.
- Build with `folio paper build <slug>`. It compiles in `.folio/build/<slug>/`, which git ignores, turns each `\fcite` into a link to the cited document on the published site (the charter's `site_url`; without one, the id prints as plain text), and fails on an id that does not resolve.
- Freeze a version at submission with `folio paper freeze <slug> --version <v>`, through the publish skill. It builds the paper, then copies `main.tex` and the PDF into `versions/<v>/`. It refuses a version name already used. It writes no journal entry: the publish skill adds one about the paper, of kind `decision`, and commits the version's folder.
- `folio paper versions <slug>` lists the versions, each with the date of the commit that froze it.

## Lifecycle

A paper is `draft` while it is being written and `live` while it is current. The source is revised freely, before and after every version. Each version is permanent from the commit that adds it: the gate compares its folder with that commit. A correction to a version is a journal entry of kind `correction` about the paper, shown as a banner; the next version carries the fix. A paper nobody will revise again becomes `historical`. The cited documents keep changing; the paper cites them by id, so its links stay valid.

## Example

```latex
\begin{abstract}
Attention computed one tile of keys at a time is exact when the softmax is rescaled as it goes.
\end{abstract}
\section{Background}
We use the definition of the softmax in \fcite{softmax}.
\begin{figure}[t]
  \includegraphics[width=\linewidth]{tiling}
  \caption{Each tile of keys rescales the running sum of the row before it.}
\end{figure}
```
