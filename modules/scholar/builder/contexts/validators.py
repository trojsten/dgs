from enschema import Schema, Optional, Regex

from core.builder.validator import FileSystemValidator, File


class ScholarValidator(FileSystemValidator):
    _schema = Schema({
        Optional(Regex(r'[\w-]+\.(png|jpg|svg|gp|py|dat)')): File,
        Optional(Regex(r'[\w-]+')): {
            Optional('problem.md'): File,
            Optional('solution.md'): File,
            Optional(Regex(r'[\w-]+\.(png|jpg|svg|gp|py|dat)')): File,
        },
        Optional('text.md'): File,
        'meta.yaml': File,
    })
