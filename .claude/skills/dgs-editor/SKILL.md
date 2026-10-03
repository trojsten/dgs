---
name: dgs-editor
description: Run and extend DGS's Flask editor and auditor (tools/editor/app.py) — how to start it, why it must run from the repository root, how a module declares its units through modules/<module>/editor.yaml, and how that descriptor mirrors module.mk's file rules. Use when starting the editor or the /audit page, adding a module descriptor, or changing which files a unit may hold.
---

# The editor and the auditor

One Flask app, two pages. Run it from the repository root:

```
uv run python tools/editor/app.py [--port 5001]
```

- `/` — the editor: pick a problem, edit its sources and `meta.yaml`, render, compile,
  lint, and read the PDF beside them. Tab indents rather than moving focus — four spaces
  in the sources, two in `meta.yaml`, to the next stop; Shift+Tab outdents; Escape leaves
  the textarea, since Tab no longer does. A selection is never replaced, only indented.
  The PDF preview is drawn by pdf.js (`static/pdfview.js`, with pdfjs-dist vendored under
  `static/vendor/pdfjs/`), not by the browser's viewer, so the editor owns the zoom -- kept in
  `localStorage` -- and the scroll offset, and a recompile or a language switch keeps both.
  "open in tab" is still the browser's own viewer, for when text needs selecting.
- `/audit` — every volume in one table, then one volume in detail: an author
  leaderboard, tag distribution, files by language, and a verdict per problem for
  translations, equation de-duplication, pictures and `values:` extraction.

**The hover answers two questions, and they come from different places.** Point at a name in
either pane — a filter, a global, a quantity attribute, a `meta.yaml` key — and the popup shows
its entry from `core/builder/reference.py`, the same table `docs/filters.md` is generated from.
F1 asks the same of whatever is under the caret, since a hover is no use to someone mid-line.
Under that, for anything evaluable, the popup shows **what it renders to here**: the tag's own
output for this problem in this language, which is the question the table cannot answer.

Two things are evaluable, and `evaluableSpans` in `static/highlight.js` is the one definition of
both: a `(§ … §)` tag, evaluated as written, and an entry's own name in the meta, for which the
tag that would reach it is synthesised — hovering `snell` under `eq:` answers for
`(§ eq.snell §)`, `v0` under `values:` for `(§ v0 §)`, `air` under `words:` for
`(§ words.air §)`. The deeper level of `values:` and `words:` is not an entry — `magnitude:` is
a reference key and `sk:` is a language — so neither gets one.

`POST /api/evaluate` does the work, in-process and writing nothing. It reads the **buffers** out
of the request rather than the files, because the whole point is to answer for the text on
screen, which is usually unsaved; and it shares `build_render_context` and `render_twice` with
`core/builder/renderer.py`, so it cannot answer differently from what `make` would write —
including whether an `eq:` display carries its `{#eq:…}` label, which depends on the open tab
through the module's `equation_numbering`. A test asserts that agreement rather than trusting it.

A meta that does not validate, or a `derived:` entry that will not evaluate, is reported in the
popup instead of a value. That is deliberate and it is strict: the build would refuse the same
meta, and a popup that quietly accepted one it will not is the single disagreement this is meant
to prevent.

One request per buffer, not one per hover. Building the context evaluates every `derived:` entry
and costs about the same for forty fragments as for one, so the first hover asks for everything
in the pane and the rest are map lookups; a keystroke in either pane, a different tab or a
different problem throws the lot away.

**It degrades rather than failing.** The three output tabs are the pipeline's three stages --
Rendered Markdown is Jinja and needs only make, TeX adds pandoc, the PDF adds all of TeX Live and
the fonts -- and `tools/editor/capabilities.py` probes for each at startup. A stage this machine
cannot do is greyed, and the pane behind it says what is missing and the command that fixes it, so
a translator with no TeX Live can still check their own rendering. `install.md` has the tiers;
`uv run python tools/editor/capabilities.py` prints the same report. `uv` is not required --
without it the app calls `make` directly with its own interpreter's directory on `PATH`.

It must run from the root, and it `chdir`s there itself: several `core` modules open
their data by a repository-relative path, so `core/i18n` fails to import from anywhere
else. Port 5000 is the default but is often taken.

Both pages learn what a module contains from `modules/<module>/editor.yaml` — where the
units live, what files they hold, and which level (`scope:`) the audit aggregates at. A
fourth module needs a descriptor and no code.

What files a unit may hold comes from `module.mk`'s two rule families —
`NABOJ_TRANSLATABLE` inside `<language>/`, `NABOJ_NONTRANSLATABLE` beside the unit — by
way of the descriptor's `targets`/`translated`, which mirror them. `core/tests/test_audit.py`
fails if the mirror stops matching, so adding a file to module.mk cannot silently cost it a
column. The audit narrows that vocabulary to what a volume actually has, and gives each
remaining file a column of its own, grouped under its language.

**The audit covers `naboj` only**, by `audit: true` in its descriptor. The checks and the
four verdicts are Náboj's conventions — a language directory per problem, `values:` and
`eq:` in a meta, a volume `problems:` list — and seminar and scholar are built differently
enough that measuring them against these would report the difference as a defect. The
editor still edits all three. If either ever wants auditing it wants its own checks, not
the flag flipped.

The audit checks live in `core/audit/`, not in the app, because they are the durable
part: `checks.py` for the source-only ones, `status.py` for the four progress verdicts,
`build.py` for the slow ones.

The conventions the checks enforce — the `values` verdict, `answer-literal`, the volume
`problems:` ordering, and what adding a check costs — stay in the root `CLAUDE.md`,
because they govern editing problems rather than running this app.
