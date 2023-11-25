from schema import Schema, Optional, Regex, Or

from core.builder.validator import FileSystemValidator
from core.utilities.schema import file


class ScholarValidator(FileSystemValidator):
    _schema = Schema({
        Regex(r'[\w-]+'): {
            Optional('problem.md'): file,
            Optional('solution.md'): file,
            Optional(Regex(r'[\w-]+\.(png|jpg|svg|gp|py|dat)')): file,
            'meta.yaml': file,
        },
        'meta.yaml': file,
    })