---
name: naboj-authoring
description: Author, edit, and debug Náboj competition problem sources (source/naboj/**) using DGS's Markdown+Jinja+LaTeX pipeline. Use whenever the user is creating a new problem, editing problem.md / solution.md / answer.md / preamble.md / meta.yaml under source/naboj/phys/*/problems/** or source/naboj/chem/*/problems/**, debugging mdcheck violations, Jinja MissingVariablesError, pandoc/XeLaTeX errors, or extending core/ or modules/naboj (new filters, new physical constants in core/data/constants.yaml, new LaTeX macros in core/latex/*.tex, new templates in modules/naboj/templates). Applies to all Náboj volumes (phys/26, phys/27, phys/28, chem/*, ...) — the format is stable across volumes with only minor differences.
---

# Náboj problem authoring (DGS)

DGS renders each problem through this pipeline:

```
source/naboj/<comp>/<vol>/problems/<pid>/<lang>/{problem,solution}.md   (Markdown + Jinja)
       + source/naboj/<comp>/<vol>/problems/<pid>/{preamble,answer,answer-also,answer-interval}.md
       + source/naboj/<comp>/<vol>/problems/<pid>/meta.yaml
  →  render/naboj/<comp>/<vol>/problems/<pid>/<lang>/*.md                (pure Markdown, no Jinja)
  →  build/naboj/<comp>/<vol>/problems/<pid>/<lang>/*.tex                (pandoc → XeLaTeX)
  →  PDF (booklet, tearoff, answers, solutions, ...)
```

Preamble + meta.yaml are prepended into the Jinja context; the Jinja renderer runs **twice** so
substituted equations get their inner tags expanded on the second pass. Then the DGS Markdown
style linter (`core/mdcheck`) runs, and pandoc converts to TeX using DGS's custom class
(`core/latex/dgs.cls`, plus `math.tex`, `symbols.tex`, `siunitx.tex`, `hacks.tex`).

## Where to start

**Route by task:**

- Authoring / editing a problem (`problem.md`, `solution.md`, `meta.yaml`, `preamble.md`,
  `answer*.md`) → read `references/layout.md`, then `references/markdown-extensions.md`.
- Using `(§ … §)` templating, `@J set …`, math filters, `Q(…)`, `const.g`, etc. →
  `references/jinja-templating.md`.
- Defining `values:` in meta.yaml, using `PhysicsQuantity`, `.eq`, `.approx`, `.widen`, ranges,
  formatting filters (`|f2`, `|g3`, `|ef2`, `|af2`, `|w(0.05)`) →
  `references/quantities-and-constants.md`.
- Using / adding custom LaTeX macros (`\Int`, `\Sum`, `\Ceil`, `\Nuclide`, `\Implies`, …) →
  `references/latex-macros.md`.
- Style linter failures (missing spaces around `=`, `\SI` vs `\qty`, label conventions,
  `\frac` in answers, …) → `references/markdown-extensions.md` §Style checker.

## Ground rules

1. **Do not invent macros.** Every math command not in vanilla amsmath comes from
   `core/latex/*.tex`. Grep `core/latex/symbols.tex` and `core/latex/math.tex` before
   introducing a new one.
2. **Use `\qty` / `\num` / `\ang` — never `\SI`.** `mdcheck` fails the build on `\SI`.
3. **Use `\Implies`, not `\implies` or `\Rightarrow`.** Same rule for `\Int`/`\Sum` over
   `\int`/`\sum`, `\Ceil{…}` over `\lceil…\rceil`, `\ang{…}` over `^\circ`.
4. **Preserve spaces around binary operators** in math: `= \approx \doteq \geq \leq \gg \ll +
   \cdot`. `mdcheck` flags each violation with a caret pointing at the column.
5. **Labels start with the problem id.** In `solution.md` you must add a
   sublabel (`{#eq:archery:hd}`). In `problem.md` you can go bare
   (`{#eq:archery}`) or sub-labelled (`{#fig:archery:diagram}`) — most
   `problem.md` equations get no label at all.
6. **Answers use `\dfrac`, not `\frac`.** `mdcheck` enforces this on `answer.md` /
   `answer-also.md` / `answer-interval.md`.
7. **Two-pass rendering matters.** If a value expands into a `\qty{…}` that itself contains
   Jinja tags (e.g. from a MathObject), it still gets rendered on the second pass. Don't
   try to escape or defer — just write the natural thing.

## Rendering pipeline entry points

- Convertor for problems: `modules.naboj.builder.renderer` (subclass of
  `core.builder.renderer.CLIInterface`). Meta.yaml + preamble.md become the context.
- Jinja setup: `core/builder/jinja.py` — see `MarkdownJinjaRenderer` for the exact filter /
  global table.
- Style linter: `core/markdown-check.py` runs `core/mdcheck/check.py` rules per line.
- Templates that assemble PDFs: `modules/naboj/templates/*.jtex` (these use `(* … *)` for
  variables, unlike `.md` files which use `(§ … §)`).
- Build orchestration: root `Makefile` + `modules/naboj/module.mk` (rules
  `NABOJ_TRANSLATABLE` for problem/solution, `NABOJ_NONTRANSLATABLE` for
  answer/answer-also/answer-interval).

## Volume differences to be aware of

- `phys/28` uses `authors:` (plural, list). `phys/27` mostly uses `author:` (singular).
  Both are tolerated; new problems should use `authors: [...]`.
- Older volumes often lack `values:` entirely; numbers are hard-coded in the Markdown.
- `chem/*` volumes use a flatter layout (`source/naboj/chem/<vol>/problems/<pid>/…`)
  and use chemistry macros (`\ce{…}`, `\Nuclide{…}`, `\chemfig{…}`). Their `sk/` may be
  the only language directory.

## Environment / build

The project uses **uv** (see recent commit "Switched to uv"). To build one problem:

```
uv run python -m modules.naboj.builder.renderer \
    -C source/naboj/phys/28/problems/archery/meta.yaml \
    -P source/naboj/phys/28/problems/archery/preamble.md \
    source/naboj/phys/28/problems/archery/en/solution.md \
    /tmp/out.md
```

Or via Make targets defined in `modules/naboj/module.mk`. Do not commit the `_minted-output`
directory (`.gitignore`d).
