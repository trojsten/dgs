import _io
from schema import Schema, Optional, Regex

from core.builder.validator import FileSystemValidator
from core.utilities.schema import valid_language


file = _io.TextIOWrapper


class NabojValidator(FileSystemValidator):
    schema = Schema({
        'problems': {
            str: {
                valid_language: {
                    'problem.md': file,
                    'solution.md': file,
                    Optional('answer-extra.md'): file,
                },
                'answer.md': file,
                Optional('answer-interval.md'): file,
                Optional('meta.yaml'): file,
                Optional(Regex(r'[a-z0-9-]+\.(png|svg|gp|py|dat)')): file,
            },
        },
        'languages': {
            valid_language: {
                'meta.yaml': file,
                'intro.jtt': file,
                'instructions-inner.jtt': file,
                'evaluators.jtt': file,
            }
        },
        'venues': {
            Regex(r'[a-z]+'): {
                'instructions-inner.jtt': file,
                'meta.yaml': file,
            },
        },
        'meta.yaml': file,
    })
