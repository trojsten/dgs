from enschema import Optional, Regex, Schema
from schema import Forbidden

from core.builder.validator import File, FileSystemValidator


def _round_schema(suffix: str) -> Schema:
    """
    What a round's directory must hold, in the markup its repository is written in.

    The two flavours differ in exactly two file names and in nothing else, which is the whole
    claim this function makes: a Typst repository is the same tree with `problem.typ` where
    `problem.md` would be. Parameterised rather than copied so that the next thing a round must
    carry is declared once.
    """
    return Schema({
        Regex(r'0[1-8]'): {
            f'problem.{suffix}': File,
            f'solution.{suffix}': File,
            # Anything else the problem carries: a data set, a photo, a Google Earth track, a
            # script the author wrote to check the answer. This used to be a whitelist of eight
            # extensions, which meant every new kind of attachment failed the whole round until
            # someone extended it -- `35/2/1/04/solved.kmz` had been stopping that round's build
            # outright. A file the build does not know how to use costs nothing; a file it
            # refuses to look at costs a PDF. Names holding whitespace are still rejected below.
            Optional(str): File,
            Forbidden(Regex(r'\s')): File,                                     # Reject anything containing whitespace
            'meta.yaml': File,
        },
        # **Temporary, and meant to be deleted along with the file.** `camp.yaml` does not
        # belong in the repository at all; it is kept only until someone confirms the camp
        # details it holds -- accommodation, transport, price -- are recorded on the website,
        # and then both the file and this line go.
        #
        # It is here because without it `35/1/1` failed validation outright with
        # `Wrong key 'camp.yaml'` and that round produced no PDF, which is too high a price for
        # a file nothing reads. Nothing does read it: the camp a template sees is
        # `semester.camp`, off the semester meta, which is a separate mechanism already typed
        # on `ContextSemester`. Six more of these sit one level up at the semester, which no
        # filesystem validator looks at, so they have never had to be declared; `35/1/1` is the
        # only one parked inside a round.
        Optional('camp.yaml'): File,
        'meta.yaml': File,
    })


class SeminarRoundValidator(FileSystemValidator):
    """A round written in Markdown, which is every seminar repository that exists today."""
    _schema = _round_schema('md')


class SeminarTypstRoundValidator(FileSystemValidator):
    """A round written in Typst, declared by `format: typst` in the competition's meta."""
    _schema = _round_schema('typ')


#: Which validator a repository takes, by the `format:` its competition meta declares.
ROUND_VALIDATORS = {
    'markdown': SeminarRoundValidator,
    'typst': SeminarTypstRoundValidator,
}
