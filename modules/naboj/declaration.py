"""
What Náboj's builders write, and the one thing the graph must read for itself.

Imported by `modules/naboj/builder/{language,venue}.py`, by `tools/ninja/generate.py` and by the
tests. Stdlib only -- see `core/builder/products.py` for why that matters and what the seam is.
"""
import pathlib

from core.builder.products import Node, Product, Root, read_scalar

#: `modules/naboj/builder/language.py`. The nine module templates are what a volume is printed
#: from; `intro` and `evaluators` come from the *language's own* directory and are written only
#: where that language has written them.
#:
#: `evaluators` is the one with a history. `NabojValidator` has always marked it optional, but the
#: loop that rendered it did so unconditionally, so a language without one died on
#: `TemplateNotFound` and could not build at all -- not even its tearoffs. Volume 26's `cs`, `es`,
#: `hu` and `pl` are exactly that case, and volume 25 has it in `sk` alone.
LANGUAGE = Node('language', (
    Product('booklet', 'booklet.jtex'),
    Product('answers', 'answers.jtex'),
    Product('constants', 'constants.jtex'),
    Product('cover', 'cover.jtex'),
    Product('online', 'online.jtex'),
    Product('evaluation', 'evaluation.jtex'),
    Product('tearoff', 'tearoff.jtex'),
    Product('problems', 'problems.jtex'),
    Product('solutions', 'solutions.jtex'),
    Product('intro', 'intro.jtex', root=Root.UNIT, optional=True),
    Product('evaluators', 'evaluators.jtex', root=Root.UNIT, optional=True),
))

#: `modules/naboj/builder/venue.py`. Two documents are handed to the same room, and the content
#: half of the instructions is per *language* rather than per venue -- it lives in the language
#: directory the venue declares, which is a sibling of the venue and not a child of it.
#:
#: **Sixteen of the ancient volumes have no instructions in any language**, because nothing
#: records what the rules of Náboj were in 2000. That is why `instructions-inner` is optional and
#: why `instructions.jtex` reaches it with `\\protectedInput`: the hole is unrecoverable rather
#: than unwritten, and `answers-modulo.pdf` is what those years are wanted for.
VENUE = Node('venue', (
    Product('instructions', 'instructions.jtex'),
    Product('answers-modulo', 'answers-modulo.jtex'),
    Product('instructions-inner', 'instructions-inner.jtex', root=Root.LANGUAGE, optional=True),
))

NODES = {'language': LANGUAGE, 'venue': VENUE}

#: What a Náboj *problem* holds, split by where it lives. A translated file sits inside the
#: language directory, a shared one beside it -- an answer in volumes `14`-`18` is a value and
#: needs no translated copy, so it is one file read once per language.
#:
#: **The authority for the file taxonomy, with three readers and one more that is pinned to it.**
#: `tools/ninja/generate.py` emits an edge per name, `modules/naboj/builder/contexts/validators.py`
#: builds its schema out of them, and `modules/naboj/editor.yaml` lists the same names as the
#: editor's tabs -- that last one is a different axis (what a human may open) and so stays a file
#: of its own, pinned against this by `core/tests/test_audit.py::TestFileFamiliesMatchTheBuild`.
#:
#: The validator used to restate them, and restated them *wrongly*: it required `answer.md` of
#: every problem where the graph emits it only where it exists, and it accepted a picture
#: extension set that had drifted from `PICTURE_SOURCES`/`PICTURE_COPIES`. Both agreed with
#: reality by accident, which is the state this file exists to end.
TRANSLATED = ('problem', 'problem-extra', 'solution', 'answer-extra')
SHARED = ('answer', 'answer-also', 'answer-interval')

#: Every extension a drawing or its data may have beside a problem. The first six are what
#: `tools/ninja/generate.py` can turn into a picture -- `PICTURE_SOURCES` then `PICTURE_COPIES` --
#: and the last three are what a `.gp` reads or a solution `include()`s.
#:
#: `pdf` is in it and was missing from the validator, which is the drift this now cannot have: a
#: problem shipping a ready-made PDF drawing builds perfectly and failed validation. Nothing in
#: the repository does today, so nobody had met it.
ASSET_EXTENSIONS = ('svg', 'tikz', 'gp', 'png', 'jpg', 'pdf', 'py', 'dat', 'tex')

#: Which Náboj competitions a builder may be pointed at, and the one list of them.
#:
#: There were three, all different: `builder.py` and `standalone.py` each wrote out these five
#: independently, and `contexts/base.py` had `phys`, `chem`, `test` enforced by a bare `assert`.
#: So `--competition junior` -- which two of the three already anticipate -- got past argparse,
#: past the builder, and died inside a context constructor with an `AssertionError` carrying no
#: message. Under `python -O` the assert is not there at all and it would have built nonsense.
#:
#: Not read off `source/naboj/`, deliberately. That directory also holds `fks-naboj` and
#: `fks-ancient`, which spell languages differently, are built by nothing and are not ours;
#: admitting them because they happen to be checked out would turn a clear argparse refusal
#: into a confusing failure much further in.
COMPETITIONS = ('phys', 'math', 'chem', 'junior', 'test')

#: A venue meta that names no language. 69 of the 144 do not, and that is not a defect: a venue
#: whose documents nobody builds needs no language, and guessing one would put a booklet in front
#: of a room in the wrong tongue.


def venue_language(meta: pathlib.Path) -> str | None:
    """
    Which language a venue's documents are set in, read straight off its `meta.yaml`.

    This is the one root a builder computes that the graph cannot ask it for:
    `BuilderNabojVenue.language_path()` reads `self.context.data['language']['id']`, which exists
    only after a context has been built and validated, and the graph builds no contexts. So the
    graph reads the key itself, and `core/tests/test_declarations.py` asserts the two agree over
    every venue meta in the checkout.

    **`None` where there is no key, and no guess.** 69 of the 144 venue metas have none -- all of
    `phys/02` and `20`-`25`, several of them empty files -- and those venues cannot build today
    for a reason that has nothing to do with this: `contexts/buildable.py` subscripts
    `i18n.languages[venue.language]` outright, so the builder raises before anything reads an
    i18n table. Falling back to the volume's language would paper over that with the wrong
    locale; raising here would be worse still, because one incomplete venue in a volume nobody
    builds would stop the generator emitting *any* scope's edges.
    """
    return read_scalar(meta, 'language')
