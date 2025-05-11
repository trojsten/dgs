from enschema import Schema, Optional, Regex
from schema import Forbidden

from core.builder.validator import FileSystemValidator, File


class SeminarRoundValidator(FileSystemValidator):
    _schema = Schema({
        Regex(r'0[1-8]'): {
            'problem.md': File,
            'solution.md': File,
            Optional(Regex(r'[\w-]+\.(png|jpg|svg|gp|py|cpp|dat|pdf)')): File,
            Forbidden(Regex(r'\s')): File,                                     # Reject anything containing whitespace
            'meta.yaml': File,
        },
        'meta.yaml': File,
    })
