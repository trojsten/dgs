import os
import datetime
from pathlib import Path
from enschema import Schema, And, Or, Regex

from core.builder import context
from core.builder.builder import get_last_commit_hash, get_branch
from core.utilities.schema import valid_language, commit_hash


class ContextNaboj(context.FileSystemContext):
    _target = None
    _subdir = None
    competitions = ['phys', 'chem', 'test']
    team = Schema({
        'id': And(int, lambda x: 0 <= x <= 9999),
        'code': str,
        'contact_email': And(str, len),
        'contact_name': And(str, len),
        'contact_phone': str,
        'contestants': str,
        'display_name': And(str, len),
        'in_school_symbol': Or(None, And(str, lambda x: len(x) == 1)),
        'language': And(str, valid_language),
        'name': object,
        'number': object,
        'school': str,
        'school_address': str,
        'school_id': int,
        'school_name': str,
        'status': str,
        'venue': And(str, len),
        'venue_code': And(str, lambda x: len(x) == 5),
        'venue_id': int,
    })
    problem = Schema({
        'id': Regex(r'[a-z0-9-]+'),
        'number': int,
    })
    _schema = Schema({
        'build': {
            'user': And(str, len),
            'dgs': {
                'hash': commit_hash,
                'branch': str,
            },
            'repo': {
                'hash': commit_hash,
                'branch': str,
            },
            'timestamp': datetime.datetime,
        }
    })

    def populate(self, repo_root: str):
        """
        Add the build info to the context. This is useful for impressum and diagnostics
        -   username of whoever built the current context
        -   dgs branch and git hash
        -   repo branch and git hash
        """
        self.add({
            'build': {
                'user': os.environ.get('USERNAME'),
                'dgs': {
                    'hash': get_last_commit_hash(),
                    'branch': get_branch(),
                },
                'repo': {
                    'hash': get_last_commit_hash(self.node_path(repo_root)),
                    'branch': get_branch(self.node_path(repo_root)),
                },
                'timestamp': datetime.datetime.now(datetime.timezone.utc),
            }
        })

    def as_tuple(self, competition: str = None, volume: int = None, sub: str = None, issue: str = None):
        assert competition in ContextNaboj.competitions

        result = []
        if competition is not None:
            result.append(competition)
            if volume is not None:
                result.append(f'{volume:02d}')
                if self._target is not None and issue is not None:
                    result.append(sub)
                    result.append(issue)
        return tuple(result)

    def ident(self, competition=None, volume=None, issue=None):
        return self.as_tuple(competition, volume, self._target, issue)

    def node_path(self, competition=None, volume=None, issue=None):
        return Path(self.root, *self.as_tuple(competition, volume, self._subdir, issue))

    def validate_repo(self, competition=None, volume=None, *args) -> None:
        super().validate_repo(competition, volume)