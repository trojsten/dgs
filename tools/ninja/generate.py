r"""
Generate `build.ninja` for one Náboj volume, as a spike against the Makefile.

**Why this exists.** The make build decides what to do with pattern rules whose prerequisites come
from `$(wildcard …)`, and a wildcard that matches nothing yields *nothing* rather than failing. A
rule then either silently does not apply -- and an existing target is declared current -- or applies
against whatever is left in `build/`. That has hidden three defects on record: `Makefile:20-23`
(`$(lang)` unset, every picture rule dying on `invalid choice`), `Makefile:146`, and a 40-page
Ukrainian booklet built for a volume that has no Ukrainian. Ninja has no pattern rules and no
implicit search: a target either has an edge here or it is `ninja: error: unknown target`.

**Why it is possible.** No `$(wildcard …)` in any of the four makefiles reads `build/` -- every
`build/` prerequisite is `$(subst source/,build/,…)` of a `source/` glob. The dependency graph is a
pure function of the source tree, so it can be computed up front.

Run:

    uv run python -m tools.ninja.generate --scope phys/29 -o build.ninja
    uv run --with ninja ninja -f build.ninja output/naboj/phys/29/languages/sk/booklet.pdf

Nothing in `Makefile` or `modules/*/module.mk` is touched; the two drive the same trees and the
point of the exercise is to diff their output.
"""
import argparse
import pathlib
import sys

from tools.ninja.ink import described
from tools.ninja.writer import Writer

#: Files a problem holds inside its language directory, and beside it. The split is
#: `modules/naboj/editor.yaml`'s `targets` / `translated`; it is repeated here rather than read
#: because the spike must not depend on the descriptor being right about a module it is testing.
#: Which fragments each document actually includes. Make expresses this with the three
#: per-language stamps `problems/<l>`, `solutions/<l>` and `answers/<l>`
#: (`modules/naboj/module.mk:321-343`); the sets are the same, named rather than stamped.
#:
#: Getting it wrong is not merely wasteful. Declaring every fragment on every document made
#: `problems.pdf` wait for a `solution.md` it never includes -- and in `FKS/42/1/1` that is a
#: solution which does not currently convert, so a booklet that builds under make did not here.
NABOJ_GROUPS = {
    'problems': ('problem', 'problem-extra'),
    'solutions': ('solution',),
    'answers': ('answer', 'answer-also', 'answer-interval', 'answer-extra'),
}
NABOJ_DOCUMENT_GROUPS = {
    'booklet': ('problems', 'solutions', 'answers'),
    'online': ('problems', 'solutions', 'answers'),
    'tearoff': ('problems', 'solutions', 'answers'),
    'problems': ('problems',),
    'solutions': ('solutions',),
    'answers': ('answers',),
    'constants': (),
    'cover': (),
    'evaluation': (),
}
#: The same, for seminar, from `modules/seminar/module.mk:171-199`.
SEMINAR_DOCUMENT_GROUPS = {
    'problems': ('problem',),
    'solutions': ('solution',),
    'solutions-full': ('problem', 'solution'),
}

#: Scholar has two kinds of issue and each has its own builder, writing three documents and two
#: respectively (`modules/scholar/builder/{handout,homework}.py`). A unit here is an *issue*,
#: which holds a `text.md` of its own and a directory per problem -- two editable levels, which
#: `modules/scholar/editor.yaml` declares as two `units:` entries.
SCHOLAR_KINDS = {
    'handouts': ('handout', ('handout-students', 'handout-solutions', 'handout-solved')),
    'homework': ('homework', ('homework-students', 'homework-solutions')),
}
#: `content` is in neither `modules/scholar/module.mk`'s `RULE_TEMPLATE_SCHOLAR` (which names
#: `text problem solution`) nor `modules/scholar/editor.yaml` (`targets: [text]`), and 28 files
#: are called that -- which is why `make output/scholar/…/handout-students.pdf` dies on the
#: XFAIL fall-through at `Makefile:186` rather than building. Taken from the tree, not from
#: either declaration.
SCHOLAR_TARGETS = ('text', 'content', 'problem', 'solution')

NABOJ_RENDERER = 'modules.naboj.builder.renderer'
SEMINAR_RENDERER = 'modules.seminar.builder.renderer'
SCHOLAR_RENDERER = 'modules.scholar.builder.renderer'

TRANSLATED = ('problem', 'problem-extra', 'solution', 'answer-extra')
SHARED = ('answer', 'answer-also', 'answer-interval')

#: What `build/%.pdf` can be made from, in the order the Makefile tries them -- which matters,
#: because a hand-drawn `.svg` matches two rules and must be copied rather than round-tripped
#: (`Makefile:227-235`). Here the choice is made once, by extension, and written down.
PICTURE_SOURCES = ('svg', 'tikz', 'gp')
PICTURE_COPIES = ('png', 'jpg', 'pdf')

#: The documents one language directory holds. `modules/naboj/builder/language.py:templates`
#: is the authority; `intro` and `evaluators` come from `i18n_templates` and are skipped when
#: their source is absent, which is the one place this generator has to guess.
LANGUAGE_DOCUMENTS = ('booklet', 'answers', 'constants', 'cover', 'online',
                      'evaluation', 'tearoff', 'problems', 'solutions')
#: Of those, the ones with a `double_xelatex` rule to a PDF in `output/`.
LANGUAGE_PDFS = ('booklet', 'problems', 'solutions', 'answers', 'constants', 'cover',
                 'evaluation', 'tearoff', 'online')

#: What `modules/seminar/builder/round.py` writes, and which of those reach `output/` as a PDF.
#: `instagram` is built but its `output/` rule is commented out in `modules/seminar/module.mk:270`;
#: it is kept here as a `.tex` so nothing is lost, and not as a PDF so nothing new appears.
ROUND_DOCUMENTS = ('problems', 'solutions', 'solutions-full', 'instagram')
ROUND_PDFS = ('problems', 'solutions', 'solutions-full')

#: A seminar problem's two fragments. Seminar is monolingual -- one language, not one of several
#: that happens to be checked out -- so there is no language directory and no shared/translated
#: split to make.
SEMINAR_TARGETS = ('problem', 'solution')

#: What `modules/naboj/builder/venue.py` writes: two from the template root, and
#: `instructions-inner.tex` per language, which it skips when the source is absent.
VENUE_DOCUMENTS = ('instructions', 'answers-modulo')


def rules(w: Writer) -> None:
    """Every command shape the volume needs, taken verbatim from the Makefile's recipes."""
    # The interpreter that generated this file, by absolute path, rather than a bare `python`
    # the way the Makefile's recipes spelled it. Bare, every invocation has to go through
    # `uv run` to put one on PATH -- which costs about 55 ms each time and fails outright if
    # you type `ninja` directly, including the generator rule rebuilding this very file.
    w.comment('Commands are the Makefile\'s, unchanged, so the two builds can be diffed.')
    w.variable('python', sys.executable)
    # Every Python step goes through the warm runner rather than starting an interpreter of
    # its own: 92 % of what one of these costs is the import of `core.builder.jinja` and the
    # pint/numpy stack under it -- 0.46 s of wall and 1.10 s of CPU, against 0.05 s to do the
    # work. `tools/runner/` carries the argument; what matters here is that the argument list
    # after the script is exactly what `python` itself would have taken, so deleting
    # `-S tools/runner/client.py` from any command below runs it the old way. So does
    # `DGS_NO_DAEMON=1`, and so does any failure to reach a daemon, which falls back by itself.
    #
    # `regenerate` is deliberately *not* among them: it rewrites `build.ninja` precisely when
    # the code a daemon is holding has changed, which is the one moment a warm interpreter is
    # the wrong thing to ask.
    w.variable('run', f'{sys.executable} -S tools/runner/client.py')
    w.newline()

    # **No pool for xelatex.** One was here as a precaution -- two runs in a directory, and
    # `-shell-escape` lets a document write anything -- and it was wrong: `-jobname` is the full
    # output path, so no two runs ever share an output name, and nothing else is written to a
    # shared name. What the precaution cost was every scrap of parallelism on the one expensive
    # step: a depth-1 pool put all 1549 xelatex edges in single file, so `-j8` bought nothing at
    # all and a picture-heavy volume ran slower than it had under make.
    w.rule('jinja',
           '$run -m $renderer $lang $in $out --context $meta',
           # `$kind` is bound by every edge, through `_rendered`.
           description=described('{a}[jinja] Rendering {x}$kind template{a} {f}$in{a} '
                                 'to {x}$kind{a} file {f}$out'))
    w.rule('pandoc_tex',
           '$run pandoc.py --format latex $lang $in $out',
           description=described('{a}[convert] Converting {x}Markdown{a} file {f}$in{a} '
                                 'to {x}TeX{a} file {f}$out'))
    w.rule('copy',
           'mkdir -p $$(dirname $out) && cp $in $out',
           # `$kind` is bound by every edge, through `_copied`: a rule block may not carry a
           # default for it, and an unbound variable would print as nothing.
           description=described('{a}Copying {x}$kind{a} file {f}$in{a} to {f}$out'))
    w.rule('i18n',
           'mkdir -p build/core/i18n && $run -m core.builder.i18n '
           "'core/i18n/' 'core/templates/' $lang -o build/core/i18n",
           description=described('{a}Building {x}i18n{a} files for {f}$lang'))
    w.rule('copy_static',
           'mkdir -p $$(dirname $out) && cp -r $src/.static/ $$(dirname $out)/ && touch $out',
           description=described('{a}Copying {x}static{a} files for {f}$src'))
    w.rule('language',
           "mkdir -p $outdir && $run -m modules.naboj.builder.language 'source/naboj/' "
           "'modules/naboj/templates/' $competition $volume $lang -o '$outdir'",
           description=described('{a}Building {x}language{a} documents for '
                                 '{f}$competition/$volume/$lang'))
    w.rule('picture_tex',
           'mkdir -p $$(dirname $out) && $run standalone.py $lang $in $out',
           description=described('{a}[standalone] Rendering {x}picture template{a} {f}$in{a} '
                                 'to {x}TeX{a} file {f}$out'))
    w.rule('svg_pdf',
           # `${out}-crop`, not `$out-crop`: a Ninja variable name may contain a hyphen, so the
           # bare form is read as a variable called `out-crop`, expands to nothing, and `mv` is
           # left with one operand. The error says `missing destination file operand`, which
           # names neither the rule nor the variable.
           'mkdir -p $$(dirname $out) && rsvg-convert --format pdf --keep-aspect-ratio '
           '--output $out $in && pdfcrop $out ${out}-crop && mv ${out}-crop $out',
           description=described('{a}[rsvg-convert] Converting {f}$in{a} '
                                 'to {x}PDF{a} file {f}$out'))
    w.rule('tikz_pdf',
           'mkdir -p $$(dirname $out) && ' + _xelatex('$in', '$out', first=True)
           + ' && ' + _xelatex('$in', '$out', first=False)
           + ' && ' + _depfile('$out'),
           description=described('{a}[xelatex] Rendering {f}$in{a} '
                                 'to {x}PDF{a} file {f}$out'),
           depfile='$out.d', deps='gcc')
    # `Makefile:350-354`, written out rather than referenced. `gpterm` carries the terminal *and*
    # its font because re-issuing `set terminal` resets the font, and the two `-e` options cannot
    # be one: gnuplot expands a macro while parsing the line it is on.
    w.rule('gnuplot_pdf',
           'mkdir -p $$(dirname $out) && cd $$(dirname $out) && gnuplot '
           '-e "set macros; gppt = 1.0 / 72; '
           '''gpterm = 'pdfcairo fontscale 1 font \\"Minion Pro, 6\\"' " '''
           '-e "set terminal @gpterm size 5, 3; '
           "set output '$$(basename $out)'; set fit quiet;\" $$(basename $in)",
           description=described('{a}[gnuplot] Rendering {f}$in{a} '
                                 'to {x}PDF{a} file {f}$out'))
    w.rule('document_pdf',
           'mkdir -p $$(dirname $out) && ' + _xelatex('$tex', '$out', first=True)
           + ' && ' + _xelatex('$tex', '$out', first=False)
           + ' && ' + _depfile('$out'),
           description=described('{a}[XeLaTeX] Compiling {x}PDF{a} file {f}$out'),
           depfile='$out.d', deps='gcc')
    w.rule('standalone_tex',
           "mkdir -p $outdir && $run -m modules.naboj.builder.standalone "
           "$competition $volume $problem $lang -o '$outdir'",
           description=described('{a}Building {x}standalone{a} for {f}$outdir'))
    w.rule('scholar_issue',
           "mkdir -p $outdir && $run -m modules.scholar.builder.$builder 'source/scholar/' "
           "'modules/scholar/templates/' $course $year $issue -o '$outdir'",
           description=described('{a}Building {x}$builder{a} for {f}$outdir'))
    w.rule('round',
           "mkdir -p $outdir && $run -m modules.seminar.builder.round 'source/seminar/' "
           "'modules/seminar/templates/' -c $competition -v $volume -s $semester -r $round "
           "-o '$outdir'",
           description=described('{a}Building {x}round{a} documents for {f}$outdir'))
    w.rule('venue',
           "mkdir -p $outdir && $run -m modules.naboj.builder.venue 'source/naboj/' "
           "'modules/naboj/templates/' $competition $volume $venue -o '$outdir'",
           description=described('{a}Building {x}venue{a} documents for '
                                 '{f}$competition/$volume/$venue'))
    w.rule('standalone_pdf',
           'mkdir -p $$(dirname $out) && ' + _xelatex('$tex', '$out', first=True)
           + ' && ' + _xelatex('$tex', '$out', first=False)
           + ' && ' + _depfile('$out'),
           description=described('{a}[XeLaTeX] Compiling {x}PDF{a} file {f}$out'),
           depfile='$out.d', deps='gcc')
    # `pdfbook2` names its own output and the recipe renames it; `pdfjam` takes `--outfile`.
    w.rule('pdfbook',
           'mkdir -p $$(dirname $out) && pdfbook2 --paper a4paper --outer-margin=30 '
           '--inner-margin=50 --top-margin=30 --bottom-margin=30 $in && '
           'mv $$(dirname $in)/$$(basename $in .pdf)-book.pdf $out',
           description=described('{a}[pdfbook2] Imposing {f}$in{a} into {f}$out'))
    w.rule('pdfjam_nup',
           'mkdir -p $$(dirname $out) && pdfjam --quiet --nup "2x1" --landscape '
           '--outfile $out $in',
           description=described('{a}[pdfjam] Imposing {f}$in{a} into {f}$out'))
    # `pdftk burst` writes one PDF per page and the count is only known after xelatex ran, so
    # the pages are not declared; the stamp is what downstream depends on.
    w.rule('burst',
           'pdftk $in burst output $$(dirname $in)/%02d.pdf && touch $out',
           description=described('{a}[pdftk] Splitting {f}$in{a} into individual pages'))
    w.rule('tearoff_zip',
           'mkdir -p $$(dirname $out) && rm -f $out && $run -m tools.ninja.zip $out $in',
           description=described('{a}Packing {x}tear-offs{a} into {f}$out'))
    w.rule('phony_clean',
           'rm -rf $paths',
           description=described('{a}Removing {f}$paths'))
    w.rule('prune',
           '$python tools/prune.py $flags',
           description=described('{a}Prune: {f}$flags'))
    w.rule('regenerate',
           '$python -m tools.ninja.generate --scope $scope -o $out',
           description=described('{a}[ninja] Regenerating {f}$out'), generator='1')
    w.newline()


#: `Makefile:68-72`. The first pass is allowed wrong cross-references, the second is not.
TEXFOT_FIRST = ("--no-interactive --ignore 'Underfull.*' "
                "--ignore 'LaTeX Warning: Hyper reference.*' "
                "--ignore 'LaTeX Warning: Reference.*' --ignore 'LaTeX Warning: Citation.*'")
TEXFOT = "--no-interactive --ignore 'Underfull.*'"


def _xelatex(source: str, target: str, *, first: bool) -> str:
    r"""
    One xelatex pass, spelled as `Makefile:85-90` spells it, plus `-recorder`.

    `-recorder` is the whole of the dependency story for a document. It costs nothing -- TeX
    writes a `.fls` listing every file it opened -- and it is the only honest answer to
    `\protectedInput`, whose path is built from a macro at run time and then tested with
    `\IfFileExists`. `tools/ninja/fls.py` turns the log into a depfile.
    """
    return ('max_print_line=1000 error_line=254 half_error_line=238 texfot '
            f'{TEXFOT_FIRST if first else TEXFOT} xelatex -file-line-error -shell-escape '
            f'-recorder -jobname=$$(echo {target} | sed s/\\.pdf$$//) -halt-on-error -synctex=1 '
            f'-interaction=nonstopmode {source}')


def _depfile(target: str) -> str:
    """The command tail that turns this run's `.fls` into the depfile Ninja reads next time."""
    return (f'$run -m tools.ninja.fls $$(echo {target} | sed s/\\.pdf$$//).fls '
            f'{target} {target}.d')


def languages_of(volume: pathlib.Path) -> list[str]:
    """
    The translations this volume has, from `languages/` on disk.

    **This is the whole point of the exercise.** Make matched any string here, so
    `…/languages/uk/booklet.pdf` was a legal target for a volume with no Ukrainian; a language
    that is not in this list simply has no edges and Ninja refuses it by name.
    """
    root = volume / 'languages'
    return sorted(child.name for child in root.iterdir() if child.is_dir()) if root.is_dir() else []


def generate(repo: pathlib.Path, scopes: list[str], out) -> dict:
    """Rules once, then the edges of every scope, then the edge that rebuilds this file."""
    w = Writer(out)
    w.comment('GENERATED by `python -m tools.ninja.generate`. Do not edit.')
    w.comment('A spike. The Makefile still builds the same trees; see tools/ninja/generate.py.')
    w.newline()
    rules(w)

    totals = {'edges': 0, 'problems': 0, 'pictures': 0, 'languages': [], 'listed': set()}
    needs = {'languages': set(), 'competitions': set()}

    # Two passes over the scopes: the first writes their edges into a buffer and collects what
    # they share, the second puts the shared edges in front. Ninja does not care about order --
    # it reads the whole file before deciding anything -- but a person reading `build.ninja`
    # does, and the core comes first in the Makefile too.
    import io
    body = io.StringIO()
    inner = Writer(body)
    inner.emitted = w.emitted          # one map across both, or a clash across the split is missed
    for scope in scopes:
        # `<module>:<scope>`; a bare scope is naboj's, which is what the spike started with.
        module, _, path = scope.rpartition(':')
        counts = (seminar_edges(repo, path, inner) if module == 'seminar'
                  else scholar_edges(repo, path, inner) if module == 'scholar'
                  else scope_edges(repo, path, inner))
        for key in ('edges', 'problems', 'pictures'):
            totals[key] += counts[key]
        totals['languages'] += counts['languages']
        totals['listed'] |= counts['listed']
        for key in ('languages', 'competitions'):
            needs[key] |= counts.get('needs', {}).get(key, set())

    totals['edges'] += core_edges(repo, w, needs)
    w.out.write(body.getvalue())

    # The names that are not files. `clean` and friends keep their `rm -rf`; `stale` and
    # `prune` are `tools/prune.py`, which is not about this build system at all -- it exists
    # because make kept intermediates it could not clean up after, and it still answers the
    # question "what is in build/ that has no source".
    w.comment('Housekeeping. `clean` removes `build/`, `distclean` also `render/` and `output/`; '
              '`stale` lists what has no source left and `prune` removes it.')
    w.build('clean', 'phony_clean', None, variables={'paths': 'build'})
    w.build('distclean', 'phony_clean', None, variables={'paths': 'build render output'})
    w.build('stale', 'prune', None, variables={'flags': ''})
    w.build('prune', 'prune', None, variables={'flags': '--delete'})
    totals['edges'] += 4
    w.newline()

    w.comment('Rerun this generator when the set of files changes -- Ninja does it itself, '
              'given the `generator` rule and something to notice the change by.')
    w.comment('**The directories, not their contents.** A file edited inside one does not change '
              'this graph; a problem or a translation added or removed does, and a directory\'s '
              'mtime moves on exactly that event and no other. `naboj_problem_dirs` in '
              'modules/naboj/module.mk:114-132 is the same trick for the same reason -- the '
              'difference is that here it is needed in one place instead of on every document.')
    w.build('build.ninja', 'regenerate', None,
            implicit=['tools/ninja/generate.py', 'tools/ninja/writer.py',
                      *sorted(totals['listed'])],
            variables={'scope': ' '.join(scopes)})
    totals['edges'] += 1
    return totals


def core_edges(repo: pathlib.Path, w: Writer, needs: dict) -> int:
    r"""
    The edges every scope shares, emitted once however many scopes there are.

    The i18n tables, and each competition's `.static/` tree. One `core.builder.i18n` invocation
    writes both the `.tex` the booklet `\input`s and the `.yaml` every pandoc run reads as
    `crossrefYaml` -- two outputs on one edge, where `Makefile:165` declares only the first and
    leaves `core/templates/crossref.jyaml` a prerequisite of nothing at all.
    """
    w.comment('==== core ' + '=' * 60)
    edges = 0
    for lang in sorted(needs['languages']):
        w.build(f'build/core/i18n/{lang}.tex', 'i18n', [f'core/i18n/{lang}.yaml'],
                implicit=['core/templates/override.jtex', 'core/templates/crossref.jyaml'],
                implicit_outputs=[f'build/core/i18n/{lang}.yaml'],
                variables={'lang': lang})
        edges += 1
    for competition in sorted(needs['competitions']):
        static = repo / 'source/naboj' / competition / '.static'
        w.build(f'build/naboj/{competition}/copy-static', 'copy_static', None,
                implicit=sorted(str(p.relative_to(repo)) for p in static.rglob('*')
                                if p.is_file()) if static.is_dir() else None,
                variables={'src': f'source/naboj/{competition}'})
        edges += 1
    w.newline()
    return edges


def scope_edges(repo: pathlib.Path, scope: str, w: Writer) -> dict:
    counts = {'edges': 0, 'languages': [], 'listed': set()}

    def listed(directory: pathlib.Path) -> pathlib.Path:
        """Record a directory whose *listing* this graph depends on, and return it."""
        if directory.is_dir():
            counts['listed'].add(str(directory.relative_to(repo)))
        return directory

    def build(*args, **kwargs):
        counts['edges'] += 1
        return w.build(*args, **kwargs)

    competition, volume_id = scope.split('/')
    volume = repo / 'source' / 'naboj' / scope
    listed(volume / 'languages')
    languages = languages_of(volume)
    problems = sorted(p.parent for p in listed(volume / 'problems').glob('*/meta.yaml'))

    w.comment(f'==== {scope} ' + '=' * 60)

    # The i18n tables and the competition's static files are shared by every scope, so they are
    # emitted once by `generate()`. Declaring them here instead gave Ninja `multiple rules
    # generate build/core/i18n/sk.tex` the moment a second volume was added -- which is Ninja
    # refusing an ambiguity make would have resolved silently by taking whichever rule it saw
    # last.
    static = f'build/naboj/{competition}/copy-static'
    counts['needs'] = {'languages': set(languages), 'competitions': {competition}}
    templates = sorted(str(q.relative_to(repo))
                       for q in (repo / 'modules/naboj/templates').rglob('*.jtex'))

    # -- pictures --------------------------------------------------------------------------------
    w.comment('Pictures. A `.svg`, `.tikz` and `.gp` are Jinja templates first; the meta beside '
              'them is the context, so a drawing can print the number the meta computes.')
    pictures = []
    for problem in problems:
        rel = listed(problem).relative_to(repo / 'source').as_posix()
        meta = (problem / 'meta.yaml').resolve()
        for extension in PICTURE_SOURCES:
            for picture in sorted(problem.glob(f'*.{extension}')):
                stem = f'{rel}/{picture.stem}'
                _rendered(build, f'render/{stem}.{extension}', f'source/{stem}.{extension}',
                          implicit=[str(meta.relative_to(repo))],
                          variables={'lang': 'sk', 'meta': str(meta),
                                     'renderer': NABOJ_RENDERER})
                pictures.append(_picture_pdf(build, w, stem, extension, problem, repo))
        for extension in PICTURE_COPIES:
            for picture in sorted(problem.glob(f'*.{extension}')):
                stem = f'{rel}/{picture.stem}'
                if _already_drawn(w, stem, extension):
                    continue
                _copied(build, f'build/{stem}.{extension}', f'source/{stem}.{extension}')
                pictures.append(f'build/{stem}.{extension}')
    w.newline()

    # -- fragments -------------------------------------------------------------------------------
    w.comment('One fragment per problem per language. A translated file lives inside the language '
              'directory; a shared one sits beside the meta and is rendered once per language.')
    fragments = {lang: {group: [] for group in NABOJ_GROUPS} for lang in languages}
    for problem in problems:
        rel = problem.relative_to(repo / 'source').as_posix()
        meta = (problem / 'meta.yaml').resolve()
        for lang in languages:
            listed(problem / lang)
            for name in TRANSLATED:
                if not (problem / lang / f'{name}.md').is_file():
                    continue
                fragments[lang][_group(name)].append(_fragment(
                    build, f'source/{rel}/{lang}/{name}.md', f'{rel}/{lang}/{name}', lang, meta,
                    repo))
            for name in SHARED:
                if not (problem / f'{name}.md').is_file():
                    continue
                fragments[lang][_group(name)].append(_fragment(
                    build, f'source/{rel}/{name}.md', f'{rel}/{lang}/{name}', lang, meta, repo))

            # The standalone: one problem, one language, one PDF. **This is the editor's
            # preview** -- `modules/naboj/editor.yaml`'s `preview:` names it and `/api/compile`
            # builds nothing else -- so leaving it out of the graph took the editor's compile
            # button with it, which is not slowness but looks like it from the outside.
            unit = f'{rel.split("/", 1)[1]}/{lang}'          # <comp>/<vol>/problems/<pid>/<lang>
            mine = [f for group in fragments[lang].values() for f in group
                    if f.startswith(f'build/{rel}/{lang}/')]
            build(f'build/naboj/{unit}/standalone.tex', 'standalone_tex', None,
                  implicit=[*templates, f'source/{rel}/meta.yaml'],
                  variables={'competition': competition, 'volume': volume_id,
                             'problem': problem.name, 'lang': lang,
                             'outdir': f'build/naboj/{unit}'})
            pdf = f'output/naboj/{unit}/standalone.pdf'
            build(pdf, 'document_pdf', None,
                  implicit=[f'build/naboj/{unit}/standalone.tex', *mine,
                            *[p for p in pictures if p.startswith(f'build/{rel}/')],
                            f'build/core/i18n/{lang}.tex', static, 'core/latex/dgs.cls'],
                  implicit_outputs=[pdf.replace('.pdf', e)
                                    for e in ('.aux', '.log', '.out', '.synctex.gz', '.fls')],
                  variables={'tex': f'build/naboj/{unit}/standalone.tex'})
    w.newline()

    # -- documents -------------------------------------------------------------------------------
    w.comment('The language documents. One builder invocation writes all of them, which Ninja '
              'takes as one edge with many outputs -- where make needs a `touch` stamp and a row '
              'of empty-recipe rules, whose trap is that an empty recipe marks a target out of '
              'date, runs nothing, and leaves the stale file in place.')
    for lang in languages:
        outdir = f'build/naboj/{scope}/languages/{lang}'
        documents = [f'{outdir}/{name}.tex' for name in LANGUAGE_DOCUMENTS]
        extra = [f'{outdir}/{name}.tex' for name in ('intro', 'evaluators')
                 if (volume / 'languages' / lang / f'{name}.jtex').is_file()]
        build(documents + extra, 'language', None,
              implicit=[*templates, static,
                        f'source/naboj/{scope}/meta.yaml',
                        f'source/naboj/{competition}/meta.yaml',
                        f'source/naboj/{scope}/languages/{lang}/meta.yaml',
                        f'source/naboj/{competition}/.static/i18n/{lang}.yaml',
                        *sorted(str((p / 'meta.yaml').relative_to(repo)) for p in problems)],
              variables={'competition': competition, 'volume': volume_id, 'lang': lang,
                         'outdir': outdir})

        for name in LANGUAGE_PDFS:
            tex = f'{outdir}/{name}.tex'
            pdf = f'output/naboj/{scope}/languages/{lang}/{name}.pdf'
            included = [f for group in NABOJ_DOCUMENT_GROUPS[name]
                        for f in fragments[lang][group]]
            build(pdf, 'document_pdf', None,
                  implicit=[tex, *included, *pictures,
                            f'build/core/i18n/{lang}.tex', static,
                            'core/latex/dgs.cls'],
                  implicit_outputs=[pdf.replace('.pdf', e)
                                    for e in ('.aux', '.log', '.out', '.synctex.gz', '.fls')],
                  variables={'tex': tex})
        # Folded for printing, and the cover two-up. Both take a finished PDF and rename it.
        build(f'output/naboj/{scope}/languages/{lang}/booklet-print.pdf', 'pdfbook',
              [f'output/naboj/{scope}/languages/{lang}/booklet.pdf'])
        build(f'output/naboj/{scope}/languages/{lang}/cover-print.pdf', 'pdfjam_nup',
              [f'output/naboj/{scope}/languages/{lang}/cover.pdf'])

        # `online.pdf` is burst into one PDF per page. The page count is known only after
        # xelatex has run, so the pages are not declared and a stamp stands for them.
        build(f'build/naboj/{scope}/languages/{lang}/online.burst', 'burst',
              [f'output/naboj/{scope}/languages/{lang}/online.pdf'])

        # Everything this language has, as one name to ask for -- `output/naboj/%/languages/<l>`
        # in the Makefile, which had to be spelled out per language there to beat make's
        # pattern-tie rules against the venue aggregate. Here it is just a phony edge.
        w.build(f'output/naboj/{scope}/languages/{lang}/all', 'phony',
                [f'output/naboj/{scope}/languages/{lang}/{name}.pdf'
                 for name in (*LANGUAGE_PDFS, 'booklet-print', 'cover-print')])
        counts['edges'] += 1
        counts['languages'].append(f'{scope}:{lang}')
    w.newline()

    # -- the tearoff archive ---------------------------------------------------------------
    if languages:
        build(f'output/naboj/{scope}/languages/tearoffs.zip', 'tearoff_zip',
              [f'output/naboj/{scope}/languages/{lang}/tearoff.pdf' for lang in languages])

    # -- venues --------------------------------------------------------------------------------
    w.comment('Venues. One `venue.py` invocation writes `instructions.tex`, `answers-modulo.tex` '
              'and, when the source is there, `instructions-inner.tex` for the venue\'s language.')
    venues = sorted(child.name for child in listed(volume / 'venues').iterdir()
                    if child.is_dir()) if (volume / 'venues').is_dir() else []
    for venue in venues:
        outdir = f'build/naboj/{scope}/venues/{venue}'
        documents = [f'{outdir}/{name}.tex' for name in VENUE_DOCUMENTS]
        build(documents, 'venue', None,
              implicit=[*templates, static,
                        f'source/naboj/{scope}/venues/{venue}/meta.yaml',
                        f'source/naboj/{scope}/meta.yaml',
                        f'source/naboj/{competition}/meta.yaml',
                        *sorted(str((p / 'meta.yaml').relative_to(repo)) for p in problems)],
              variables={'competition': competition, 'volume': volume_id, 'venue': venue,
                         'outdir': outdir})
        for name in VENUE_DOCUMENTS:
            pdf = f'output/naboj/{scope}/venues/{venue}/{name}.pdf'
            build(pdf, 'document_pdf', None,
                  implicit=[f'{outdir}/{name}.tex', *pictures, static, 'core/latex/dgs.cls',
                            *[f'build/core/i18n/{l}.tex' for l in languages]],
                  implicit_outputs=[pdf.replace('.pdf', e)
                                    for e in ('.aux', '.log', '.out', '.synctex.gz', '.fls')],
                  variables={'tex': f'{outdir}/{name}.tex'})
        w.build(f'output/naboj/{scope}/venues/{venue}/all', 'phony',
                [f'output/naboj/{scope}/venues/{venue}/{name}.pdf' for name in VENUE_DOCUMENTS])
        counts['edges'] += 1
    w.newline()

    # -- aggregates ----------------------------------------------------------------------------
    w.comment('The names a person types. Every one is a `phony` edge over a list computed here, '
              'where make had to generate a rule per language and lean on stem length.')
    w.build(f'output/naboj/{scope}/booklets', 'phony',
            [f'output/naboj/{scope}/languages/{lang}/booklet.pdf' for lang in languages])
    w.build(f'output/naboj/{scope}/languages', 'phony',
            [f'output/naboj/{scope}/languages/{lang}/all' for lang in languages]
            + ([f'output/naboj/{scope}/languages/tearoffs.zip'] if languages else []))
    w.build(f'output/naboj/{scope}/venues', 'phony',
            [f'output/naboj/{scope}/venues/{venue}/all' for venue in venues])
    w.build(f'output/naboj/{scope}/all', 'phony',
            [f'output/naboj/{scope}/languages', f'output/naboj/{scope}/venues'])
    counts['edges'] += 4
    w.newline()

    counts['problems'] = len(problems)
    counts['pictures'] = len(pictures)
    return counts


def seminar_edges(repo: pathlib.Path, scope: str, w: Writer) -> dict:
    """
    One seminar round: `FKS/42/1/1`.

    Much the smaller half of the build, and the shape is simpler in one way that matters --
    seminar is monolingual, so there is no language dimension at all and `pathlang` resolves to
    `sk` everywhere. What it adds is `.py` listings: `(§ include('x.py') §)` inlines a program
    sitting beside the solution, and `module.mk` copies the same file into `output/` for the
    reader to download.
    """
    counts = {'edges': 0, 'languages': [], 'listed': set()}

    def listed(directory: pathlib.Path) -> pathlib.Path:
        if directory.is_dir():
            counts['listed'].add(str(directory.relative_to(repo)))
        return directory

    def build(*args, **kwargs):
        counts['edges'] += 1
        return w.build(*args, **kwargs)

    competition, volume_id, semester, round_id = scope.split('/')
    root = repo / 'source' / 'seminar' / scope
    problems = sorted(p.parent for p in listed(root).glob('*/meta.yaml'))

    w.comment(f'==== seminar/{scope} ' + '=' * 50)

    counts['needs'] = {'languages': {'sk'}, 'competitions': set()}
    templates = sorted(str(p.relative_to(repo))
                       for p in (repo / 'modules/seminar/templates').rglob('*.jtex'))

    fragments = {name: [] for name in SEMINAR_TARGETS}
    pictures = []
    for problem in problems:
        rel = listed(problem).relative_to(repo / 'source').as_posix()
        meta = (problem / 'meta.yaml').resolve()
        # the programs a solution lists, copied for the reader as well as inlined by `include()`
        for program in sorted(problem.glob('*.py')):
            _copied(build, f'output/{rel}/{program.name}', f'source/{rel}/{program.name}')
        for extension in PICTURE_SOURCES:
            for picture in sorted(problem.glob(f'*.{extension}')):
                stem = f'{rel}/{picture.stem}'
                _rendered(build, f'render/{stem}.{extension}', f'source/{stem}.{extension}',
                          implicit=[str(meta.relative_to(repo))],
                          variables={'lang': 'sk', 'meta': str(meta),
                                     'renderer': SEMINAR_RENDERER})
                pictures.append(_picture_pdf(build, w, stem, extension, problem, repo))
        for extension in PICTURE_COPIES:
            for picture in sorted(problem.glob(f'*.{extension}')):
                stem = f'{rel}/{picture.stem}'
                if _already_drawn(w, stem, extension):
                    continue
                _copied(build, f'build/{stem}.{extension}', f'source/{stem}.{extension}')
                pictures.append(f'build/{stem}.{extension}')
        for name in SEMINAR_TARGETS:
            if (problem / f'{name}.md').is_file():
                fragments[name].append(_fragment(build, f'source/{rel}/{name}.md',
                                                 f'{rel}/{name}', 'sk', meta, repo,
                                                 SEMINAR_RENDERER))

    outdir = f'build/seminar/{scope}'
    build([f'{outdir}/{name}.tex' for name in ROUND_DOCUMENTS], 'round', None,
          implicit=[*templates,
                    f'source/seminar/{scope}/meta.yaml',
                    *sorted(str((p / 'meta.yaml').relative_to(repo)) for p in problems)],
          variables={'competition': competition, 'volume': volume_id, 'semester': semester,
                     'round': round_id, 'outdir': outdir})

    for name in ROUND_PDFS:
        pdf = f'output/seminar/{scope}/{name}.pdf'
        included = [f for kind in SEMINAR_DOCUMENT_GROUPS[name] for f in fragments[kind]]
        build(pdf, 'document_pdf', None,
              implicit=[f'{outdir}/{name}.tex', *included, *pictures,
                        'build/core/i18n/sk.tex', 'core/latex/dgs.cls'],
              implicit_outputs=[pdf.replace('.pdf', e)
                                for e in ('.aux', '.log', '.out', '.synctex.gz', '.fls')],
              variables={'tex': f'{outdir}/{name}.tex'})

    w.build(f'output/seminar/{scope}/all', 'phony',
            [f'output/seminar/{scope}/{name}.pdf' for name in ROUND_PDFS])
    counts['edges'] += 1
    w.newline()

    counts['problems'] = len(problems)
    counts['pictures'] = len(pictures)
    return counts


def scholar_edges(repo: pathlib.Path, scope: str, w: Writer) -> dict:
    """
    One scholar year: `TA1/2018`.

    The shape neither other module has: **two editable levels**. An issue (`handouts/02`) holds
    its own `text.md` *and* a directory per problem, each with `problem.md` and `solution.md`,
    and one builder invocation turns the lot into three documents (or two, for homework).
    """
    counts = {'edges': 0, 'languages': [], 'listed': set()}

    def listed(directory: pathlib.Path) -> pathlib.Path:
        if directory.is_dir():
            counts['listed'].add(str(directory.relative_to(repo)))
        return directory

    def build(*args, **kwargs):
        counts['edges'] += 1
        return w.build(*args, **kwargs)

    course, year = scope.split('/')
    root = repo / 'source' / 'scholar' / scope
    w.comment(f'==== scholar/{scope} ' + '=' * 50)

    # Scholar's `.static/` trees -- `source/scholar/{STA,TA1}/.static` -- get no
    # `copy_static` edge and are a prerequisite of nothing, where every naboj document
    # takes its competition's. Recorded rather than guessed at: scholar builds under
    # neither system today, so a fix here could not be checked against anything.
    counts['needs'] = {'languages': {'sk'}, 'competitions': set()}
    templates = sorted(str(p.relative_to(repo))
                       for p in (repo / 'modules/scholar/templates').rglob('*.jtex'))

    units, pictures = 0, []
    for kind, (builder, documents) in SCHOLAR_KINDS.items():
        if not (root / kind).is_dir():
            continue
        for issue in sorted(i for i in listed(root / kind).iterdir() if i.is_dir()):
            units += 1
            issue_rel = issue.relative_to(repo / 'source').as_posix()
            # the issue's own text, then one directory per problem below it
            places = [issue, *sorted(c for c in listed(issue).iterdir() if c.is_dir())]
            fragments = []
            for place in places:
                rel = place.relative_to(repo / 'source').as_posix()
                meta = place / 'meta.yaml'
                if not meta.is_file():
                    continue
                for extension in PICTURE_SOURCES:
                    for picture in sorted(place.glob(f'*.{extension}')):
                        stem = f'{rel}/{picture.stem}'
                        _rendered(build, f'render/{stem}.{extension}',
                                  f'source/{stem}.{extension}',
                                  implicit=[f'source/{rel}/meta.yaml'],
                                  variables={'lang': 'sk', 'meta': str(meta.resolve()),
                                             'renderer': SCHOLAR_RENDERER})
                        pictures.append(_picture_pdf(build, w, stem, extension, place, repo))
                for extension in PICTURE_COPIES:
                    for picture in sorted(place.glob(f'*.{extension}')):
                        stem = f'{rel}/{picture.stem}'
                        if _already_drawn(w, stem, extension):
                            continue
                        _copied(build, f'build/{stem}.{extension}', f'source/{stem}.{extension}')
                        pictures.append(f'build/{stem}.{extension}')
                for name in SCHOLAR_TARGETS:
                    if (place / f'{name}.md').is_file():
                        fragments.append(_fragment(build, f'source/{rel}/{name}.md',
                                                   f'{rel}/{name}', 'sk', meta.resolve(), repo,
                                                   SCHOLAR_RENDERER))

            outdir = f'build/{issue_rel}'
            build([f'{outdir}/{name}.tex' for name in documents], 'scholar_issue', None,
                  implicit=[*templates, f'source/{issue_rel}/meta.yaml'],
                  variables={'builder': builder, 'course': course, 'year': year,
                             'issue': issue.name, 'outdir': outdir})
            for name in documents:
                pdf = f'output/{issue_rel}/{name}.pdf'
                build(pdf, 'document_pdf', None,
                      implicit=[f'{outdir}/{name}.tex', *fragments, *pictures,
                                'build/core/i18n/sk.tex', 'core/latex/dgs.cls'],
                      implicit_outputs=[pdf.replace('.pdf', e)
                                        for e in ('.aux', '.log', '.out', '.synctex.gz', '.fls')],
                      variables={'tex': f'{outdir}/{name}.tex'})
            w.build(f'output/{issue_rel}/all', 'phony',
                    [f'output/{issue_rel}/{name}.pdf' for name in documents])
            counts['edges'] += 1

        w.build(f'output/scholar/{scope}/{kind}', 'phony',
                [f'output/scholar/{scope}/{kind}/{i.name}/all'
                 for i in sorted(x for x in (root / kind).iterdir() if x.is_dir())])
        counts['edges'] += 1
    w.newline()

    counts['problems'] = units
    counts['pictures'] = len(pictures)
    return counts


def _already_drawn(w: Writer, stem: str, extension: str) -> bool:
    """
    Whether a drawing already produces this path, so the copy beside it must not.

    `seminar/FKS/35/1/2/02` holds both `svah.svg` and `svah.pdf`, and both want to become
    `build/…/svah.pdf`. Make picked the SVG, silently, by rule order -- `build/%.pdf: render/%.svg`
    at `Makefile:213` is tried before the `.pdf` copy at `:350`, and make takes the first rule
    whose prerequisites can be made. Keep that answer, and say so rather than relying on the
    order two loops happen to run in; Ninja would otherwise refuse the graph outright, which is
    how this was found.
    """
    return extension == 'pdf' and w.has(f'build/{stem}.pdf')


def _group(name: str) -> str:
    """Which of the three per-language sets a fragment belongs to."""
    return next(group for group, names in NABOJ_GROUPS.items() if name in names)


def _fragment(build, source: str, stem: str, lang: str, meta: pathlib.Path,
              repo: pathlib.Path, renderer: str | None = None) -> str:
    """`source/…/x.md` → `render/…/x.md` → `build/…/x.tex`, the two steps every fragment takes."""
    _rendered(build, f'render/{stem}.md', source,
              implicit=[str(meta.relative_to(repo))],
              variables={'lang': lang, 'meta': str(meta),
                         'renderer': renderer or NABOJ_RENDERER})
    build(f'build/{stem}.tex', 'pandoc_tex', [f'render/{stem}.md'],
          implicit=[f'build/core/i18n/{lang}.yaml'],
          variables={'lang': lang})
    return f'build/{stem}.tex'


#: What a template is called in the line the build prints. The jinja step serves four formats,
#: and the Makefile's single `jinja` macro called every one of them a "Markdown template" --
#: true of the 161 fragments in a volume and not of its 30 pictures.
TEMPLATE_KINDS = {'md': 'Markdown', 'gp': 'gnuplot', 'svg': 'SVG', 'tikz': 'TikZ'}


def _rendered(build, target: str, source: str, **kwargs):
    """A jinja edge that says which format it is rendering. See `_copied`."""
    kind = TEMPLATE_KINDS.get(pathlib.Path(source).suffix.lstrip('.'), 'template')
    variables = {'kind': kind, **kwargs.pop('variables', {})}
    return build(target, 'jinja', [source], variables=variables, **kwargs)


def _copied(build, target: str, source: str, **kwargs):
    """
    A copy edge that says what kind of file it is copying, which is all the description wants.

    The Makefile spelled that out at each call -- `$(call _copy,PNG)`, `$(call _copy,SVG)` --
    and the suffix is where it came from every time, so it is taken from the path here.
    """
    kind = pathlib.Path(source).suffix.lstrip('.').upper()
    variables = {'kind': kind or 'source', **kwargs.pop('variables', {})}
    return build(target, 'copy', [source], variables=variables, **kwargs)


def _picture_pdf(build, w: Writer, stem: str, extension: str, problem: pathlib.Path,
                 repo: pathlib.Path) -> str:
    """The three routes a drawing takes to the `.pdf` the booklet includes."""
    if extension == 'svg':
        build(f'build/{stem}.pdf', 'svg_pdf', [f'render/{stem}.svg'])
    elif extension == 'tikz':
        build(f'build/{stem}.tikz.tex', 'picture_tex', [f'render/{stem}.tikz'],
              implicit=['core/templates/standalone.jtex'], variables={'lang': 'sk'})
        build(f'build/{stem}.pdf', 'tikz_pdf', [f'build/{stem}.tikz.tex'])
    else:
        data = sorted(str(p.relative_to(repo / 'source')) for p in problem.glob('*.dat'))
        for name in data:
            _copied(build, f'build/{name}', f'source/{name}')
        _copied(build, f'build/{stem}.gp', f'render/{stem}.gp',
                implicit=[f'build/{name}' for name in data])
        build(f'build/{stem}.pdf', 'gnuplot_pdf', [f'build/{stem}.gp'])
    return f'build/{stem}.pdf'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('--scope', required=True, nargs='+',
                        help='one or more, e.g. phys/29 seminar:FKS/42/1/1; '
                             '`all` for every scope of every module')
    parser.add_argument('-o', '--output', type=pathlib.Path, default=pathlib.Path('build.ninja'))
    parser.add_argument('--repo', type=pathlib.Path, default=pathlib.Path('.'))
    args = parser.parse_args()

    repo = args.repo.resolve()
    scopes = args.scope
    if 'all' in scopes:
        scopes = [s for s in scopes if s != 'all']
        scopes += sorted(str(p.parent.relative_to(repo / 'source/naboj'))
                         for p in (repo / 'source/naboj').glob('*/*/problems')
                         if (p.parent / 'languages').is_dir())
        scopes += sorted(f'seminar:{p.relative_to(repo / "source/seminar")}'
                         for p in (repo / 'source/seminar').glob('*/*/*/*')
                         if p.is_dir() and any(p.glob('*/meta.yaml')))
        scopes += sorted(f'scholar:{p.relative_to(repo / "source/scholar")}'
                         for p in (repo / 'source/scholar').glob('*/*')
                         if p.is_dir() and (p / 'handouts').is_dir() or (p / 'homework').is_dir())
    with args.output.open('w') as out:
        counts = generate(repo, scopes, out)
    print(f"{args.output}: {counts['edges']} edges, {len(scopes)} scopes, "
          f"{counts['problems']} problems, {counts['pictures']} pictures, "
          f"{len(counts['languages'])} scope-languages")
    return 0


if __name__ == '__main__':
    sys.exit(main())
