from pathlib import Path
from schema import Schema, Optional, And, Regex

from core.builder import context
from core.utils.schema import valid_language


class ContextNaboj(context.FileSystemContext):
    team = Schema({
        'id': And(str, len),
        'language': And(str, valid_language),
        'name': And(str, len),
        Optional('venue'): int,
        'number': int,
    })
    problem = Schema({
        'id': Regex(r'[a-z0-9-]+'), 'number': int
    })

    def ident(self, competition=None, volume=None, target_type=None, target=None):
        return (
            self.default(competition),
            self.default(volume, lambda x: f'{x:02d}'),
            self.default(target_type),
            self.default(target),
        )

    def node_path(self, competition=None, volume=None, target_type=None, target=None):
        return Path(self.root, *self.ident(competition, volume, target_type, target))

