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
    # The other writer, from the same rendered Markdown. A fragment is to a page what a
    # `.tex` is to a PDF, so it lands in `build/` and the assembly into `output/` is the `page`
    # rule below. The two writers disagree -- maths above all -- and where they disagree the web
    # is the half nobody looks at, which is the reason it is built at all.
    w.rule('pandoc_html',
           '$run pandoc.py --format html $lang $in $out',
           description=described('{a}[convert] Converting {x}Markdown{a} file {f}$in{a} '
                                 'to {x}HTML{a} fragment {f}$out'))
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
    # A picture in the one format a browser wants, converted from **the PDF the LaTeX path
    # already built** -- so the web picture and the printed one cannot drift. `pdftocairo` and
    # not `dvisvgm --pdf`: dvisvgm reads line widths and embedded rasters wrongly, which is a
    # hairline turned into a heavy frame and a bitmap smeared into the corner (`Makefile:276-299`
    # has the whole account). A hand-drawn `.svg` short-circuits this and is copied instead.
    w.rule('pdf_svg',
           'mkdir -p $$(dirname $out) && pdftocairo -svg $in $out',
           description=described('{a}[pdftocairo] Rendering {f}$in{a} '
                                 'to {x}SVG{a} file {f}$out'))
    # A gnuplot plot is drawn twice by gnuplot rather than converted, one terminal each. The two
    # disagree about their units -- the `svg` terminal counts CSS pixels, 96 to the inch, where
    # `pdfcairo` counts points and hides a `fontscale 0.5` -- so `gppt` is 4/3 here against 1/72
    # there and the font is 8 against 6. The same type at the same size on the same canvas, said
    # in each terminal's own units.
    w.rule('gnuplot_svg',
           'mkdir -p $$(dirname $out) && cd $$(dirname $out) && gnuplot '
           '-e "set macros; gppt = 4.0 / 3; '
           '''gpterm = 'svg font \\"Minion Pro, 8\\"' " '''
           '-e "set terminal @gpterm size 480, 288; '
           "set output '$$(basename $out)'; set fit quiet;\" $$(basename $in) && "
           # A script that sets a terminal of its own wins over the `-e` above, and gnuplot then
           # writes a PDF into a file named `.svg` with no error anywhere -- `FKS/42/1/1/03` did
           # it from a `blocks:` entry, which is a `.gp` no grep over `source/**/*.gp` can see,
           # and the page showed three blank figures.
           '{ head -c 5 $$(basename $out) | grep -q "<" || { echo "$out is not an SVG: does '
           'its script (or a blocks: entry) set its own terminal?" >&2; '
           'rm -f $$(basename $out); exit 1; }; }',
           description=described('{a}[gnuplot] Rendering {f}$in{a} '
                                 'to {x}SVG{a} file {f}$out'))
    # One unit's fragments into `<outdir>/index.html`, with the pictures it names copied in
    # beside it and its maths typeset, so the directory opens from `file://` with nothing else
    # present. The pictures it copies are not declared: which ones they are is decided by
    # reading the fragments, and they are a copy of files this graph already builds.
    w.rule('page',
           'mkdir -p $outdir && $run -m core.html.page $unit $lang $outdir --module $module',
           description=described('{a}[page] Assembling {f}$unit{a} into {x}HTML{a} page '
                                 '{f}$outdir/index.html'))
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
    return sorted(child.name for child in root.iterdir()
                  if child.is_dir() and _visible(child)) if root.is_dir() else []


def generate(repo: pathlib.Path, scopes: list[str], out) -> dict:
    """Rules once, then the edges of every scope, then the edge that rebuilds this file."""
    w = Writer(out)
    w.comment('GENERATED by `python -m tools.ninja.generate`. Do not edit.')
    w.comment('A spike. The Makefile still builds the same trees; see tools/ninja/generate.py.')
    w.newline()
    rules(w)

    totals = {'edges': 0, 'problems': 0, 'pictures': 0, 'languages': [],
              'listed': set(), 'read': set()}
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
        totals['read'] |= counts.get('read', set())
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
    w.comment('A handful of *files* are in there too. A venue meta names the language its '
              'documents are set in, which decides which i18n table they need, and that is a '
              'fact no directory listing holds -- so the file itself is watched, or changing '
              '`language:` would leave the graph pointing at the locale it used to say.')
    w.build('build.ninja', 'regenerate', None,
            implicit=['tools/ninja/generate.py', 'tools/ninja/writer.py',
                      *sorted(totals['listed']), *sorted(totals['read'])],
            variables={'scope': ' '.join(scopes)})
    totals['edges'] += 1

    w.newline()
    w.comment('And a `phony` for each of those directories, which is what makes *removing* one '
              'recoverable. An input with no rule that has gone missing is a hard error -- '
              '`\'source/naboj/phys/29/problems/amusement-speed/es\', needed by '
              '\'build.ninja\', missing and no known rule to make it` -- and it is '
              'unrecoverable, because the edge that would notice the removal is the one Ninja '
              'is refusing to run. A phony whose output does not exist is simply dirty, so the '
              'generator reruns and the directory leaves the graph. Deleting a language cost a '
              'hand-run generator until this was here.')
    for directory in sorted(totals['listed']):
        w.build(directory, 'phony', None)
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
    counts = {'edges': 0, 'languages': [], 'listed': set(), 'read': set()}

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
    problems = sorted(p.parent for p in listed(volume / 'problems').glob('*/meta.yaml')
                      if _visible(p.parent))

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
    pictures, drawings = [], []
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
                printed, shown = _picture(build, w, stem, extension, problem, repo)
                pictures.append(printed)
                drawings.append(shown)
        for extension in PICTURE_COPIES:
            for picture in sorted(problem.glob(f'*.{extension}')):
                stem = f'{rel}/{picture.stem}'
                if _already_drawn(w, stem, extension):
                    continue
                _copied(build, f'build/{stem}.{extension}', f'source/{stem}.{extension}')
                pictures.append(f'build/{stem}.{extension}')
                # A raster goes to the page as it is; a PDF copied in is converted like any
                # other drawing.
                drawings.append(_picture_svg(build, w, stem, extension) if extension == 'pdf'
                                else f'build/{stem}.{extension}')
    w.newline()

    # -- fragments -------------------------------------------------------------------------------
    w.comment('One fragment per problem per language. A translated file lives inside the language '
              'directory; a shared one sits beside the meta and is rendered once per language.')
    fragments = {lang: {group: [] for group in NABOJ_GROUPS} for lang in languages}
    pages = {lang: [] for lang in languages}
    for problem in problems:
        rel = problem.relative_to(repo / 'source').as_posix()
        meta = (problem / 'meta.yaml').resolve()
        for lang in languages:
            listed(problem / lang)
            web = []
            for name in TRANSLATED:
                if not (problem / lang / f'{name}.md').is_file():
                    continue
                tex, fragment = _fragment(
                    build, f'source/{rel}/{lang}/{name}.md', f'{rel}/{lang}/{name}', lang, meta,
                    repo)
                fragments[lang][_group(name)].append(tex)
                web.append(fragment)
            for name in SHARED:
                if not (problem / f'{name}.md').is_file():
                    continue
                tex, fragment = _fragment(
                    build, f'source/{rel}/{name}.md', f'{rel}/{lang}/{name}', lang, meta, repo)
                fragments[lang][_group(name)].append(tex)
                web.append(fragment)

            # The page: the same problem in the same language, for a browser. Only where there
            # is something to assemble -- `page.py` refuses an empty unit, and rightly, so a
            # declared edge with no fragments would be an edge that cannot run.
            if web:
                pages[lang].append(_page(build, rel, lang, 'naboj', fragments=web,
                                         pictures=_beside(drawings, rel), nested=True))

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
        # Every page of this volume in this language. Not folded into `all`, which is the
        # Makefile's reading too: the documents are what a volume is run from, and the pages
        # are a second output of the same sources rather than part of the first.
        w.build(f'output/naboj/{scope}/languages/{lang}/pages', 'phony', pages[lang])
        counts['edges'] += 2
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
                    if child.is_dir() and _visible(child)) if (volume / 'venues').is_dir() else []
    for venue in venues:
        venue_meta = f'source/naboj/{scope}/venues/{venue}/meta.yaml'
        # **A venue is set in its own language, which need not be one of the volume's.** Volume
        # 29 has `en` and `sk` and runs in Praha and Olomouc, so its Czech venue documents
        # `\input{build/core/i18n/cs.tex}` -- a file nothing asked for, because the edges were
        # taking the *volume's* languages. The whole of `all` failed on it, 34 documents at
        # once, and it was invisible under make, whose `i18n.stamp` built every locale whether
        # anything wanted it or not.
        venue_language = _venue_language(repo / venue_meta)
        counts['needs']['languages'] |= {venue_language} - {None}
        counts['read'].add(venue_meta)
        outdir = f'build/naboj/{scope}/venues/{venue}'
        documents = [f'{outdir}/{name}.tex' for name in VENUE_DOCUMENTS]
        build(documents, 'venue', None,
              implicit=[*templates, static,
                        venue_meta,
                        f'source/naboj/{scope}/meta.yaml',
                        f'source/naboj/{competition}/meta.yaml',
                        *sorted(str((p / 'meta.yaml').relative_to(repo)) for p in problems)],
              variables={'competition': competition, 'volume': volume_id, 'venue': venue,
                         'outdir': outdir})
        for name in VENUE_DOCUMENTS:
            pdf = f'output/naboj/{scope}/venues/{venue}/{name}.pdf'
            build(pdf, 'document_pdf', None,
                  implicit=[f'{outdir}/{name}.tex', *pictures, static, 'core/latex/dgs.cls',
                            *([f'build/core/i18n/{venue_language}.tex']
                              if venue_language else [])],
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
    w.build(f'output/naboj/{scope}/pages', 'phony',
            [f'output/naboj/{scope}/languages/{lang}/pages' for lang in languages])
    w.build(f'output/naboj/{scope}/venues', 'phony',
            [f'output/naboj/{scope}/venues/{venue}/all' for venue in venues])
    w.build(f'output/naboj/{scope}/all', 'phony',
            [f'output/naboj/{scope}/languages', f'output/naboj/{scope}/venues'])
    counts['edges'] += 5
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
    problems = sorted(p.parent for p in listed(root).glob('*/meta.yaml') if _visible(p.parent))

    w.comment(f'==== seminar/{scope} ' + '=' * 50)

    counts['needs'] = {'languages': {'sk'}, 'competitions': set()}
    templates = sorted(str(p.relative_to(repo))
                       for p in (repo / 'modules/seminar/templates').rglob('*.jtex'))

    # `source/seminar/<competition>/.static/` is what every round of that competition inputs:
    # the format override, the logo, and the intro and rules templates. `module.mk` copied the
    # whole tree with one `cp -r` whose own target it never touched, so it depended on nothing
    # and ran on every build; here each file is an edge and the documents name what they read.
    static = []
    for path in sorted(p for p in listed(repo / 'source/seminar' / competition / '.static')
                       .rglob('*') if p.is_file()):
        listed(path.parent)
        source = path.relative_to(repo).as_posix()
        target = source.replace('source/', 'build/', 1)
        _copied(build, target, source)
        static.append(target)

    fragments = {name: [] for name in SEMINAR_TARGETS}
    pictures, drawings, pages = [], [], []
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
                printed, shown = _picture(build, w, stem, extension, problem, repo)
                pictures.append(printed)
                drawings.append(shown)
        for extension in PICTURE_COPIES:
            for picture in sorted(problem.glob(f'*.{extension}')):
                stem = f'{rel}/{picture.stem}'
                if _already_drawn(w, stem, extension):
                    continue
                _copied(build, f'build/{stem}.{extension}', f'source/{stem}.{extension}')
                pictures.append(f'build/{stem}.{extension}')
                drawings.append(_picture_svg(build, w, stem, extension) if extension == 'pdf'
                                else f'build/{stem}.{extension}')
        web = []
        for name in SEMINAR_TARGETS:
            if (problem / f'{name}.md').is_file():
                tex, fragment = _fragment(build, f'source/{rel}/{name}.md',
                                          f'{rel}/{name}', 'sk', meta, repo,
                                          SEMINAR_RENDERER)
                fragments[name].append(tex)
                web.append(fragment)
        # A seminar page sits in the problem directory, not in a language directory under it:
        # seminar is monolingual, which `modules/seminar/editor.yaml` says by carrying no
        # `languages:` key and which `page.py` reads from there.
        if web:
            pages.append(_page(build, rel, 'sk', 'seminar', fragments=web,
                               pictures=_beside(drawings, rel), nested=False))

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
              implicit=[f'{outdir}/{name}.tex', *included, *pictures, *static,
                        'build/core/i18n/sk.tex', 'core/latex/dgs.cls'],
              implicit_outputs=[pdf.replace('.pdf', e)
                                for e in ('.aux', '.log', '.out', '.synctex.gz', '.fls')],
              variables={'tex': f'{outdir}/{name}.tex'})

    w.build(f'output/seminar/{scope}/all', 'phony',
            [f'output/seminar/{scope}/{name}.pdf' for name in ROUND_PDFS])
    w.build(f'output/seminar/{scope}/pages', 'phony', pages)
    counts['edges'] += 2
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

    counts['needs'] = {'languages': {'sk'}, 'competitions': set()}
    templates = sorted(str(p.relative_to(repo))
                       for p in (repo / 'modules/scholar/templates').rglob('*.jtex'))

    # `source/scholar/<course>/.static/`, which every document of that course `\input`s, copied
    # one file to an edge exactly as seminar's is. It used to be a prerequisite of nothing at
    # all, on the grounds that scholar built under neither system so a fix could not be checked;
    # it builds now, and the first thing it did was stop at `File
    # 'build/scholar/STA/.static/format-override.tex' not found`.
    static = []
    for path in sorted(p for p in listed(repo / 'source/scholar' / course / '.static')
                       .rglob('*') if p.is_file()):
        listed(path.parent)
        source = path.relative_to(repo).as_posix()
        target = source.replace('source/', 'build/', 1)
        _copied(build, target, source)
        static.append(target)

    # **Fragments but no pages**, which is the one asymmetry with the other two modules.
    # `page.py` collects the targets `modules/scholar/editor.yaml` declares, and that descriptor
    # says `targets: [text]` where 28 of this module's issues hold a `content.md` instead -- so
    # an issue page would be an edge that could only ever fail with `no fragments to assemble`.
    # The `.html` fragments are still built, because those are what the editor's HTML tab shows
    # and they are right whatever the descriptor calls them. Settling `content` against `text`
    # is scholar's own question and is noted at `SCHOLAR_TARGETS`.
    units, pictures = 0, []
    for kind, (builder, documents) in SCHOLAR_KINDS.items():
        if not (root / kind).is_dir():
            continue
        for issue in sorted(i for i in listed(root / kind).iterdir()
                            if i.is_dir() and _visible(i)):
            units += 1
            issue_rel = issue.relative_to(repo / 'source').as_posix()
            # the issue's own text, then one directory per problem below it
            places = [issue, *sorted(c for c in listed(issue).iterdir()
                                     if c.is_dir() and _visible(c))]
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
                        # The `.svg` the second half of this emits is unreferenced here and
                        # is still worth having: `build/<x>.svg` is a target anyone may ask
                        # for, and it is the same picture the booklet prints.
                        printed, _ = _picture(build, w, stem, extension, place, repo)
                        pictures.append(printed)
                for extension in PICTURE_COPIES:
                    for picture in sorted(place.glob(f'*.{extension}')):
                        stem = f'{rel}/{picture.stem}'
                        if _already_drawn(w, stem, extension):
                            continue
                        _copied(build, f'build/{stem}.{extension}', f'source/{stem}.{extension}')
                        pictures.append(f'build/{stem}.{extension}')
                        if extension == 'pdf':
                            _picture_svg(build, w, stem, extension)
                for name in SCHOLAR_TARGETS:
                    if (place / f'{name}.md').is_file():
                        tex, _ = _fragment(build, f'source/{rel}/{name}.md',
                                           f'{rel}/{name}', 'sk', meta.resolve(), repo,
                                           SCHOLAR_RENDERER)
                        fragments.append(tex)

            outdir = f'build/{issue_rel}'
            build([f'{outdir}/{name}.tex' for name in documents], 'scholar_issue', None,
                  implicit=[*templates, f'source/{issue_rel}/meta.yaml'],
                  variables={'builder': builder, 'course': course, 'year': year,
                             'issue': issue.name, 'outdir': outdir})
            for name in documents:
                pdf = f'output/{issue_rel}/{name}.pdf'
                build(pdf, 'document_pdf', None,
                      implicit=[f'{outdir}/{name}.tex', *fragments, *pictures, *static,
                                'build/core/i18n/sk.tex', 'core/latex/dgs.cls'],
                      implicit_outputs=[pdf.replace('.pdf', e)
                                        for e in ('.aux', '.log', '.out', '.synctex.gz', '.fls')],
                      variables={'tex': f'{outdir}/{name}.tex'})
            w.build(f'output/{issue_rel}/all', 'phony',
                    [f'output/{issue_rel}/{name}.pdf' for name in documents])
            counts['edges'] += 1

        w.build(f'output/scholar/{scope}/{kind}', 'phony',
                [f'output/scholar/{scope}/{kind}/{i.name}/all'
                 for i in sorted(x for x in (root / kind).iterdir()
                                 if x.is_dir() and _visible(x))])
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
              repo: pathlib.Path, renderer: str | None = None) -> tuple[str, str]:
    """
    `source/…/x.md` → `render/…/x.md` → `build/…/x.{tex,html}`.

    One Jinja stage, one language, **two writers**. The `.tex` goes to xelatex and the `.html`
    goes into a page, and both are made from the same rendered Markdown -- which is the whole
    point of the arrangement, since a second route to the web would be a second chance for the
    two to disagree about what the problem says.
    """
    _rendered(build, f'render/{stem}.md', source,
              implicit=[str(meta.relative_to(repo))],
              variables={'lang': lang, 'meta': str(meta),
                         'renderer': renderer or NABOJ_RENDERER})
    build(f'build/{stem}.tex', 'pandoc_tex', [f'render/{stem}.md'],
          implicit=[f'build/core/i18n/{lang}.yaml'],
          variables={'lang': lang})
    build(f'build/{stem}.html', 'pandoc_html', [f'render/{stem}.md'],
          implicit=[f'build/core/i18n/{lang}.yaml'],
          variables={'lang': lang})
    return f'build/{stem}.tex', f'build/{stem}.html'


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


def _picture(build, w: Writer, stem: str, extension: str, problem: pathlib.Path,
             repo: pathlib.Path) -> tuple[str, str]:
    """
    The routes a drawing takes to the two formats it is wanted in.

    `build/<stem>.pdf` is what the booklet includes and `build/<stem>.svg` is what a page
    shows, and **it is the same picture** -- see `_picture_svg` for why that matters.
    """
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
    return f'build/{stem}.pdf', _picture_svg(build, w, stem, extension)


def _picture_svg(build, w: Writer, stem: str, extension: str) -> str:
    """
    The same picture, in the one format a browser wants.

    **There is no separate web drawing.** A TikZ drawing, a PDF copied in and a `.gp` all reach
    the page through the artefact the booklet prints, so the two cannot drift -- the first two
    by conversion and the plot by being drawn a second time in the `svg` terminal, which is one
    step shorter and takes the PDF parser out of the chain for the files that provoked the
    conversion bug. A hand-drawn `.svg` is copied: round-tripping it through a PDF would cost
    two conversions to arrive where it started.

    `w.has` because a picture with two sources of the same name reaches this twice -- the same
    guard `_already_drawn` applies on the PDF side, and for the same reason.
    """
    target = f'build/{stem}.svg'
    if w.has(target):
        return target
    if extension == 'svg':
        _copied(build, target, f'render/{stem}.svg')
    elif extension == 'gp':
        build(target, 'gnuplot_svg', [f'build/{stem}.gp'])
    else:
        build(target, 'pdf_svg', [f'build/{stem}.pdf'])
    return target


#: What a page's maths is set with when the engine is `latex`, which is the default: the
#: `\input`s of `core/templates/mathpage.jtex`. Every document edge gets these from xelatex's
#: own `-recorder`; a page runs its xelatex inside `core.html.texmath`, where there is no
#: recorder to read, so they are named here instead.
MATHPAGE_INPUTS = ('core/templates/mathpage.jtex', 'core/latex/fonts.tex',
                   'core/latex/utilities.tex', 'core/latex/math.tex',
                   'core/latex/symbols.tex', 'core/latex/siunitx.tex')


def _page(build, rel: str, lang: str, module: str, *, fragments: list, pictures: list,
          nested: bool) -> str:
    """
    One unit's fragments assembled into a page, which is what goes in `output/`.

    `nested` is the module's own answer to where a fragment lives: Náboj holds a directory per
    language inside a problem, so its page is `<problem>/<lang>/index.html`; seminar and scholar
    are monolingual and theirs sits in the unit directory. `page.py` reads the same fact out of
    `modules/<module>/editor.yaml`, which is why the module is passed rather than guessed from
    the path.
    """
    outdir = f'output/{rel}/{lang}' if nested else f'output/{rel}'
    build(f'{outdir}/index.html', 'page', None,
          implicit=[*fragments, *pictures, f'build/core/i18n/{lang}.tex',
                    'core/templates/page.jhtml', 'core/html/page.css', *MATHPAGE_INPUTS],
          variables={'unit': f'build/{rel}', 'lang': lang, 'module': module, 'outdir': outdir})
    return f'{outdir}/index.html'


def _visible(path: pathlib.Path) -> bool:
    """
    A directory whose name begins with a dot is not content, and nothing may treat it as one.

    Two were being built as though they were. `scholar/STA/2023/homework/02/.priors` is a draft
    kept beside the real problems: it was rendered, and failed on a meta the problem schema
    refuses. `seminar/FKS/.template` is the scaffolding a new volume is copied from, and
    `--scope all` made six scopes out of it. Neither is a defect in the sources -- a leading dot
    is how a filesystem has always said *this is not one of the others*, and `.static/` sits
    beside the units in every module without anyone mistaking it for one.
    """
    return not path.name.startswith('.')


def _venue_language(meta: pathlib.Path) -> str | None:
    """
    The one thing in this generator read out of a file rather than off a directory listing.

    A venue's documents are set in the venue's language, which decides the i18n table they
    `\\input`, and no listing anywhere holds that fact -- so it is read here, and the meta goes
    into the generator edge's inputs so that changing `language:` regenerates the graph.

    A line scan rather than `yaml.safe_load`, because this module imports nothing outside the
    standard library and `tools/ninja/bootstrap.py` leans on that: its last-resort path runs the
    generator under whatever `python3` is on PATH, where the project's packages are not
    importable. `language:` is a plain scalar in every venue meta that has one, and the schema
    requires it to be one, so there is no YAML here to get wrong.

    **`None` where there is no key, and no guess.** 69 of the 144 venue metas have none -- all
    of `phys/02` and `20`-`25`, several of them empty files -- and those venues cannot build
    today for a reason that has nothing to do with this graph: `contexts/buildable.py:66`
    subscripts `i18n.languages[venue.language]` outright, so the builder raises before anything
    reads an i18n table. Falling back to the volume's language would paper over that with the
    wrong locale; raising here would be worse still, because one incomplete venue in a volume
    nobody builds would stop the generator emitting *any* scope's edges.
    """
    for line in meta.read_text(encoding='utf-8').splitlines():
        key, separator, value = line.partition(':')
        if (separator and key.strip() == 'language'
                and (language := value.split('#')[0].strip().strip('\'"'))):
            return language
    return None


def _beside(drawings: list, rel: str) -> list:
    """The pictures that sit in this unit's own directory, which are the ones its page names."""
    return [picture for picture in drawings if picture.rsplit('/', 1)[0] == f'build/{rel}']


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

        def named(root: pathlib.Path, pattern: str):
            """Every directory matching `pattern` under `root`, by its path relative to it.

            `pathlib.glob` is not the `glob` module: `*` matches a leading dot here, which is
            how `seminar:FKS/.template/1/1` became six scopes of a scaffolding directory. Every
            part has to be visible, not only the last -- `.template/1/1` ends in `1`.
            """
            for path in root.glob(pattern):
                relative = path.relative_to(root)
                if path.is_dir() and all(not part.startswith('.') for part in relative.parts):
                    yield path, relative

        scopes += sorted(str(relative.parent)
                         for path, relative in named(repo / 'source/naboj', '*/*/problems')
                         if (path.parent / 'languages').is_dir())
        scopes += sorted(f'seminar:{relative}'
                         for path, relative in named(repo / 'source/seminar', '*/*/*/*')
                         if any(path.glob('*/meta.yaml')))
        # `A and (B or C)`. Written without the brackets this was `(A and B) or C`, so a
        # `homework/` directory got in whether or not its parent was a directory at all.
        scopes += sorted(f'scholar:{relative}'
                         for path, relative in named(repo / 'source/scholar', '*/*')
                         if ((path / 'handouts').is_dir() or (path / 'homework').is_dir()))
    with args.output.open('w') as out:
        counts = generate(repo, scopes, out)
    print(f"{args.output}: {counts['edges']} edges, {len(scopes)} scopes, "
          f"{counts['problems']} problems, {counts['pictures']} pictures, "
          f"{len(counts['languages'])} scope-languages")
    return 0


if __name__ == '__main__':
    sys.exit(main())
