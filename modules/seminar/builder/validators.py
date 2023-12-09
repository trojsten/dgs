from enschema import Schema, Optional, Regex

from core.builder.validator import FileSystemValidator, File


class SeminarRoundValidator(FileSystemValidator):
    _schema = Schema({
        Regex(r'0[1-8]'): {
            'problem.md': File,
            'solution.md': File,
            Optional(Regex(r'[\w-]+\.(png|jpg|svg|gp|py|dat)')): File,
            'meta.yaml': File,
        },
        'meta.yaml': File,
    })