from enschema import Optional, Regex, Schema
from schema import Forbidden

from core.builder.validator import File, FileSystemValidator


class SeminarRoundValidator(FileSystemValidator):
    _schema = Schema({
        Regex(r'0[1-8]'): {
            'problem.md': File,
            'solution.md': File,
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
        'meta.yaml': File,
    })
