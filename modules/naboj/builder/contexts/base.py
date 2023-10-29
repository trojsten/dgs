import datetime
import subprocess
from pathlib import Path
from schema import Schema, Optional, And, Regex

from core.builder import context
from core.utilities.schema import valid_language


class ContextNaboj(context.FileSystemContext):
    target = None
    subdir = None
    competitions = ['phys', 'chem']
    team = Schema({
        'id': And(int, lambda x: x >= 0 and x <= 9999),
        'contact_email': And(str, len),
        'code': str,
        'language': And(str, valid_language),
        'display_name': And(str, len),
        'venue_code': And(str, lambda x: len(x) == 5),
        Optional('venue'): int,
        'number': int,
    })
    problem = Schema({
        'id': Regex(r'[a-z0-9-]+'),
        'number': int,
    })
    schema = Schema({
        'hash': str,
        'timestamp': datetime.datetime
    })

    def populate(self, competition):
        # Add the hash of the current HEAD of the repository as "hash"
        self.add({
            'hash': subprocess.check_output(
                ["git", "rev-parse", "--short", "--verify", "master"],
                cwd=self.node_path(competition)
            ).decode().rstrip("\n"),
            'timestamp': datetime.datetime.now(datetime.timezone.utc)
        })

    def as_tuple(self, competition: str = None, volume: int = None, sub: str = None, issue: str = None):
        assert competition in ContextNaboj.competitions

        result = []
        if competition is not None:
            result.append(competition)
            if volume is not None:
                result.append(f'{volume:02d}')
                if self.target is not None:
                    result.append(sub)
                    if issue is not None:
                        result.append(issue)
        return tuple(result)

    def ident(self, competition=None, volume=None, issue=None):
        return self.as_tuple(competition, volume, self.target, issue)

    def node_path(self, competition=None, volume=None, target=None, issue=None):
        return Path(self.root, *self.as_tuple(competition, volume, self.subdir, issue))
