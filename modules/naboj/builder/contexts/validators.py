from enschema import Optional, Regex, Schema
from schema import Forbidden

from core.builder.products import Root
from core.builder.validator import File, FileOrLink, FileSystemValidator
from core.utilities.schema import valid_language
from modules.naboj import declaration

#: `png|jpg|svg|…`, for the one place a schema wants a pattern rather than a list.
ASSETS = '|'.join(declaration.ASSET_EXTENSIONS)

#: Which roots resolve to `languages/<lang>/`. Two nodes put files there and they call it
#: different things, because the name is relative to the node: for the *language* builder it is
#: `UNIT`, its own directory; for the *venue* builder it is `LANGUAGE`, a sibling's.
IN_A_LANGUAGE_DIRECTORY = (Root.UNIT, Root.LANGUAGE)

#: What a language directory may hold besides its meta: every product any builder takes from it.
#:
#: Read off the declaration instead of listed, because the two had contradicted each other and
#: nothing could see it. `intro.jtex` was **required** here while the declaration calls it
#: optional and `written()` skips it -- so a language that has not written one fails validation
#: from a builder whose own declaration says it need not exist. Every `phys` and `chem` language
#: happens to have one; the four that do not are in `fks-naboj`, which nothing builds.
LANGUAGE_FILES = {
    Optional(product.template): FileOrLink
    for node in declaration.NODES.values()
    for product in node.products if product.root in IN_A_LANGUAGE_DIRECTORY
}


#: What one language directory of a problem may hold.
LANGUAGE_DIRECTORY = {
            **{Optional(f'{name}.md'): FileOrLink for name in declaration.TRANSLATED},
            # This language's translated words, flat `term: text`. Named rather than
            # swept up by a `\.yaml` pattern, because it is the only YAML that belongs
            # inside a language directory and a pattern there would admit a meta.yaml
            # one level too deep -- which is a real mistake, and one nothing else
            # catches: the renderer reads the meta beside the *problem*, so a stray one
            # here is simply never read. `File`, not `FileOrLink`: a mirrored
            # translation points its prose at another language and must still spell its
            # own words, which is the whole reason they are not in the `.md`.
            Optional('words.yaml'): File,
    Optional(Regex(rf'[\w-]+\.({ASSETS})')): FileOrLink,
    Forbidden(Regex(r'\s')): File,  # Reject anything containing whitespace
}


def problems(*, language_required: bool) -> dict:
    """
    What a problem directory may hold -- and whether it must hold a translation at all.

    **A volume's problem must**: a problem with no language directory is in no booklet, so it is
    a defect there and the schema says so. **A pool's need not**: `phys/pool/stuck-rover` is a
    `rover.py` and nothing else, which is what a reservoir of unwritten problems looks like.
    That single stub, and one symlinked drawing, are the whole reason the pool would not
    validate -- neither has anything to do with the missing `languages/` the error led with.
    """
    language = {valid_language: LANGUAGE_DIRECTORY} if language_required \
        else {Optional(valid_language): LANGUAGE_DIRECTORY}
    return {
        str: {
            **language,
            # **Optional, every one of them.** `answer.md` was required, and the graph has
            # never agreed: it emits the edge `if (problem / 'answer.md').is_file()`. A
            # problem whose answer is a picture, or which has not been given one yet, builds
            # and failed to validate.
            **{Optional(f'{name}.md'): File for name in declaration.SHARED},
            Optional('meta.yaml'): File,
            Forbidden(Regex(r'\s')): File,  # Reject anything containing whitespace
            # **`FileOrLink`, because sharing a drawing is a symlink.** CLAUDE.md says so
            # outright -- "Sharing one drawing between two problems is a symlink, not an
            # `include()`: the two can end up in different volumes, and a path written into the
            # text is the fragile half of that" -- and this said `File`, which refuses one.
            # `phys/pool/troll-69-limits` points its `object.svg` at `troll-69`'s.
            Optional(Regex(rf'[\w-]+\.({ASSETS}|md)')): FileOrLink,
        },
    }

#: A **volume**: problems, the languages it is printed in, the venues it is run at, and its own
#: meta naming the running order.
VOLUME = Schema({
    'problems': problems(language_required=True),
    'languages': {
        valid_language: {
            'meta.yaml': File,
            **LANGUAGE_FILES,
            Optional('online'): {
                'language.png': FileOrLink,
                'signin.png': FileOrLink,
                'welcome.png': FileOrLink,
                'problems.png': FileOrLink,
                'instructions-online-inner.md': FileOrLink,
            }
        }
    },
    Optional('venues'): {
        # Nothing else: the content half of a venue's instructions is per *language* and
        # lives in the language directory the venue names, which is a sibling and not a
        # child. An `instructions-inner.tex` entry survived here from before that move and
        # matched no file in the repository.
        Optional(Regex(r'\w+')): {
            'meta.yaml': File,
        },
    },
    'meta.yaml': File,
})

#: A **pool**: problems and nothing else.
#:
#: `phys/pool` and `chem/pool` are reservoirs -- problems that have not been set yet, picked
#: from and moved into a volume when they are. There is no running order, so no scope meta; no
#: booklet, so no `languages/`; and nobody is sitting an exam, so no `venues/`. Validating one
#: against `VOLUME` asked for all three and failed on every pool in the repository, which is
#: why `phys/pool` was the one volume of thirty-four that would not validate.
POOL = Schema({
    'problems': problems(language_required=False),
})


class NabojValidator(FileSystemValidator):
    """
    What a Náboj volume's -- or pool's -- directory tree may contain.

    **The file names come from `modules/naboj/declaration.py`**, which is the module's own
    statement of what its problems hold and what its builders write. They used to be written out
    again here, and the copy had drifted in four places -- a required `intro.jtex` the
    declaration calls optional, a required `answer.md` the graph emits only where it exists, a
    picture extension list missing `pdf`, and a `venues/<v>/instructions-inner.tex` left behind
    when that file moved into the language directory. All four agreed with reality by accident:
    no problem ships a PDF drawing, every built language has an intro, every problem has an
    answer. The first one that does not would have met a validator contradicting the builder.
    """

    _schema = VOLUME

    @property
    def schema(self):
        """
        `VOLUME` normally; `POOL` for a pool, which is a different shape and not a defective one.

        Decided by the directory's own name, which is also what moving a problem out of a pool
        and into a volume changes. A volume with no translations yet is still a volume.
        """
        return POOL if self.root.name == 'pool' else VOLUME

    def __init__(self, *path):
        super().__init__(*path)
        self.debug = False

    # **No `perform_extra_checks`.** Two used to live here -- one comparing each problem's set
    # of translations against its neighbour's, one asking whether every translation of a problem
    # carries the same files -- and they are `core/audit`'s `translation-set` and `presence`,
    # written twice. The audit's versions have an id, a severity, a location per unit, an
    # `audit: {ignore: [...]}` opt-out and a page to appear on; these printed `Warning: ...` to
    # stdout on every language and venue edge of every volume, and failed nothing.
    #
    # A validator says whether the tree is shaped the way the builders require. Whether the
    # content in it is consistent is the auditor's question, asked where it can be answered
    # without a build -- and, for a pool, asked differently, since nothing there is shipping.
