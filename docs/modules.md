# Adding a module

A module is two trees with the same name. `modules/<name>/` is ours and is committed here;
`source/<name>/` is somebody's content, is gitignored, holds no gitlinks, and is cloned in by
hand — the `sources:` list in the descriptor is the only record of what to clone, and the editor
shows it when it finds nothing to edit.

Three exist: `naboj` (translated, a problem per directory, a volume per scope), `seminar`
(monolingual, a round per scope) and `scholar` (monolingual, two kinds of issue per course).

Write the content first. Everything below is derived from the shape of the source tree, and
changing that shape afterwards is the one change that touches every file in this list at once.

---

## The pieces, in the order to write them

### 1. `modules/<name>/editor.yaml` — the descriptor

The editor and the audit learn the whole module from this file; `tools/editor/descriptors.py`
names no module anywhere, so these two need a descriptor and no code. Copy
`modules/naboj/editor.yaml`, which is the one with the comments.

```yaml
label: Brevity
audit: false          # see below; this is Náboj's conventions, not a quality switch
languages: false      # a unit holds a directory per language
scope: volume         # the level the audit page aggregates at
units:
  - glob: '*/*/problems/*'            # relative to source/<name>/
    levels: [competition, volume, kind, problem]
    targets: [problem, solution]      # every file a unit may hold, in tab order
    translated: [problem, solution]   # the subset living inside <language>/
    render: 'render/<name>/{unit}/{language}/{target}.md'
    preview: 'output/<name>/{unit}/{language}/standalone.pdf'
sources:
  - path: source/<name>/thing
    url: git@github.com:…
```

`tex` and `html` are **derived** from `render` rather than written out, because the relation is
the build's own and `_fragment` is the single funnel every `.md` edge goes through. A module that
ever stops following that rule sets `tex_override`; nothing does.

### 2. `modules/<name>/declaration.py` — what a builder writes

At module level beside `editor.yaml`, **not** inside `builder/`, so its independence is visible.
It is stdlib-only and imports `core.builder.products` and nothing else: the graph generator
imports it to ask what the module produces, and has no business dragging pint and jinja2 in to
find out.

```python
from core.builder.products import Node, Product, Root

ROUND = Node('round', (
    Product('problems', 'problems.jtex'),
    Product('solutions', 'solutions.jtex'),
    Product('intro', 'intro.jtex', root=Root.UNIT, optional=True),
))

NODES = {'round': ROUND}
```

One `Node` per builder — per *thing one invocation writes a set of files for*. `Root` says which
directory the template is resolved against: `TEMPLATES` the module's own, `UNIT` the node's source
directory, `LANGUAGE` a sibling node's. `optional` means *the author may not have written it*.

### 3. `modules/<name>/templates/`

`.jtex` for a document, `.jyaml` for a data file; the names in the declaration resolve here. A
document extends a `base.jtex` of yours, which opens `\documentclass{dgs}` — the class is
`core/latex/dgs.cls` and every module shares it. `modules/seminar/templates/base.jtex` is the
smallest one. `standalone.jtex` is the single-unit
preview the editor compiles.

### 4. `modules/<name>/builder/`

A base class carrying `module` and the module's command-line arguments, and one subclass per node:

```python
class BuilderRound(BuilderBrevity):
    _target = 'round'
    _root_context_class = context.ContextBooklet
    _renderer_class = StaticRenderer
    _node = declaration.ROUND

if __name__ == '__main__':
    BuilderRound().build_templates()
```

`ident()` and `path()` are the two abstract methods; `roots()` is overridden only by a node with a
non-`TEMPLATES` product, and `product_ident()` only by one that renames its outputs
(`core/builder/i18n.py` is the only one in the repository). `build_templates()` is inherited and
is not yours to override — that is the whole point of the declaration.

### 5. `modules/<name>/builder/renderer.py`

A `CLIInterface` subclass with the module's `StandaloneContext` schema, and the file taxonomy:

```python
class CLIInterface(renderer.CLIInterface, ABC):
    equation_numbering = {'text.md': True, 'problem.md': False, 'solution.md': True}
    figure_captions    = {'text.md': True, 'problem.md': False, 'solution.md': True}
```

**Both directions, every file**, not a list of exceptions — reading it should tell you the whole
taxonomy. A file neither mentions keeps its numbers and its captions, which is the conservative
default and deliberately so.

### 6. `modules/<name>/i18n/` — optional

Only if the module's documents print words core's tables do not have. `modules/scholar/i18n/` is
the example and its context reads it directly; Náboj keeps its equivalents in the content tree,
under `<competition>/.static/i18n/`.

### 7. `tools/ninja/generate.py` — the one file outside the module

**This is the part that is not module-agnostic, and it is the bulk of the work.** Three places:

- a `<name>_edges(repo, scope, w) -> dict` beside `seminar_edges`, which writes the scope's edges
  and returns `{'edges', 'problems', 'pictures', 'languages', 'listed', 'read'}`, plus
  `'needs': {'languages', 'competitions'}`;
- the dispatch in `generate()`, which reads `<module>:<scope>` and sends a bare scope to naboj;
- the discovery in `main()` under `--scope all`, which is what makes a scope reachable without
  anyone typing it.

Plus a `w.rule(...)` per builder invocation, spelling the command line the builder's argparse
takes: `launch`, `template_root`, the module's own arguments, `-o <outdir>`.

The PDF lists stay here — `build/` cannot tell you which `.tex` XeLaTeX is pointed at, and it is
partly policy — but each is asserted to be a **subset** of its node's products, so add yours to
`core/tests/test_declarations.py`'s `TestTheGraphAgreesWithTheBuilders` when you write it.

### 8. `modules/<name>/tests/`

For anything needing the content checked out. `pytestmark = pytest.mark.skipif(not
pathlib.Path('source/<name>').is_dir(), …)` at the top, and **a basename no other module uses** —
there are no `__init__.py` under `modules/` and pytest refuses two test modules with the same
name. `core/tests/` must keep passing in a checkout with no content repositories at all.

---

## What to watch for

1. **The seam.** A builder declares the set of files one invocation writes; the graph declares
   everything else. The test for which side a fact belongs on: *if you could learn it by running
   the builder and listing `<outdir>`, it is the builder's; if you could only learn it by reading
   a template or a recipe, it is the graph's.* Restating a builder's document list in
   `generate.py` is exactly the duplication the declarations replaced.

2. **`optional` is never true for a `TEMPLATES` product.** A module template that is missing is a
   bug and must raise `TemplateNotFound`; marking it optional turns a typo into a document that
   silently never appears. Asserted over every declaration in the repository.

3. **Declaration order is render order**, and that is load-bearing, not tidy — a template that
   reads a file a sibling has just written sees the difference.

4. **A template that `\input`s an optional product must use `\protectedInput`**, or guard the
   include behind a Jinja condition. A bare `\input` of a file nobody wrote is an `Emergency stop`
   naming nothing; two documents died that way. `test_declarations.py` checks it for you, but only
   over `modules/naboj/templates` — widen it when you add a module with optional products.

5. **Every builder goes under `if __name__ == '__main__'`.** Importing one otherwise parses
   `sys.argv` and writes files; it took the job-runner daemon down once.

6. **Nothing under `modules/` has an `__init__.py`**, and that is what makes the declarations
   cheap to import. Do not add one.

7. **`audit: true` is not a quality switch.** The audit's checks and its four progress verdicts
   encode Náboj's conventions — a language directory per problem, `values:` and `eq:` in a meta, a
   volume `problems:` list. Turning it on for a module built differently reports the difference as
   a defect. A module that wants auditing wants its own checks.

8. **`languages: true` means one of several, not one.** Seminar is monolingual — it has a language
   and no language *dimension* — so it carries no `translated:` and its fragments sit in the unit
   directory rather than below it. Getting this wrong makes `page.py` assemble a page out of
   whatever lies beside the unit.

9. **Declare the languages your scope needs.** `core_edges` emits `build/core/i18n/<lang>.tex`
   only for the languages the scopes asked for through `needs['languages']`; miss it and a
   document `\input`s a table nothing builds.

10. **`listed()` and `read` are what make the graph regenerate.** A directory whose *listing* the
    graph depends on goes in `listed`; a file it reads a fact out of goes in `read`. Both become
    implicit inputs of `build.ninja` and get a `phony` of their own, which is what makes removing
    one recoverable — without the phony, deleting a directory leaves Ninja refusing to run the
    very edge that would notice.

11. **Two more places still name modules by hand**, and they are easy to miss because nothing
    fails loudly: `core/audit/build.py`'s `TARGETS` (which documents a build check compiles) and
    `core/mdcheck/check.py`'s label parsing, which has a `case` per module and raises
    `Unsupported module` on anything else.

12. **The gate is the graph diff.** The generator is a pure function of the source tree, about a
    second for `--scope all`, so generate before and after and compare the output sets, the rules
    and the inputs. Then build one scope end to end and compare the `build/**/*.tex`, not the
    PDFs — those carry a timestamp.

---

## Checklist

```
source/<name>/                       content, cloned by hand
modules/<name>/editor.yaml           editor + audit learn everything here
modules/<name>/declaration.py        stdlib only; one Node per builder
modules/<name>/templates/            .jtex, including base and standalone
modules/<name>/builder/builder.py    module name, shared arguments
modules/<name>/builder/<node>.py     _node, _target, contexts; under if __name__
modules/<name>/builder/renderer.py   schema, equation_numbering, figure_captions
modules/<name>/builder/standalone.py the editor's single-unit preview
modules/<name>/builder/context*.py   the context tree
modules/<name>/i18n/                 only if the documents need words core lacks
modules/<name>/tests/                unique basenames, skipif on source/
tools/ninja/generate.py              <name>_edges, the dispatch, --scope all, the rules
core/tests/test_declarations.py      add the module to MODULES
```
