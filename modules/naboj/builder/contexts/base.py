from pathlib import Path
from schema import Schema, And, Optional, Regex

from core.builder import context
from core.utils.schema import valid_language


class ContextNaboj(context.Context):
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

    def node_path(self, competition=None, volume=None, target_type=None, target=None):
        return Path(
            self.root,
            '' if competition is None else competition,
            '' if volume is None else f'{volume:02d}',
            '' if target_type is None else target_type,
            '' if target is None else target
        )

