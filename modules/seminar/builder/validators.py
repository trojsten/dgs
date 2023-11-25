from schema import Optional, Regex

from core.builder.validator import FileSystemValidator
from core.utilities.schema import Schema, file


class SeminarRoundValidator(FileSystemValidator):
    _schema = Schema({
        Regex(r'0[1-8]'): {
            'problem.md': file,
            'solution.md': file,
            Optional(Regex(r'[\w-]+\.(png|jpg|svg|gp|py|dat)')): file,
            'meta.yaml': file,
        },
        'meta.yaml': file,
    })