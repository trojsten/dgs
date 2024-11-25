from enschema import Schema, Optional, Regex

from core.builder.validator import FileSystemValidator, File, FileOrLink


data = Regex(r'[\w-]+\.(png|jpg|svg|gp|py|dat|tsv)')


class HandoutValidator(FileSystemValidator):
    _schema = Schema({
        Optional(data): FileOrLink,
        Optional(Regex(r'[\w-]+')): {
            Optional('problem.md'): File,
            Optional('solution.md'): File,
            Optional('meta.yaml'): File,
            Optional(data): FileOrLink,
            Optional(Regex(r'[\w-]+')): {
                Optional('problem.md'): File,
                Optional('solution.md'): File,
                'meta.yaml': File,
                Optional(data): FileOrLink,
            },
        },
        Optional('text.md'): File,
        'meta.yaml': File,
    })


class HomeworkValidator(FileSystemValidator):
    _schema = Schema({
        Optional(data): FileOrLink,
        Optional(Regex(r'[\w-]+')): {
            Optional('problem.md'): File,
            Optional('solution.md'): File,
            Optional('meta.yaml'): File,
            Optional(data): FileOrLink,
            Optional(Regex(r'[\w-]+')): {
                Optional('problem.md'): File,
                Optional('solution.md'): File,
                'meta.yaml': File,
                Optional(data): FileOrLink,
            },
        },
        Optional('text.md'): File,
        'meta.yaml': File,
    })
