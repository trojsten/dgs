from enschema import Schema, Optional, Regex

from core.builder.validator import FileSystemValidator, File, FileOrLink


class ScholarValidator(FileSystemValidator):
    _schema = Schema({
        Optional(Regex(r'[\w-]+\.(png|jpg|svg|gp|py|dat)')): FileOrLink,
        Optional(Regex(r'[\w-]+')): {
            Optional('problem.md'): File,
            Optional('solution.md'): File,
            Optional(Regex(r'[\w-]+\.(png|jpg|svg|gp|py|dat)')): FileOrLink,
        },
        Optional('text.md'): File,
        'meta.yaml': File,
    })
