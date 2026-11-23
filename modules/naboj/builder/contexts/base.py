import datetime
import getpass
import os
from pathlib import Path

from enschema import And, Optional, Or, Regex, Schema

from core.builder.builder import get_branch, get_describe, get_last_commit_hash
from core.builder.context.tree import FileSystemTreeContext
from core.builder.validator import CommitHash
from core.utilities.schema import valid_language
from modules.naboj import declaration
from modules.naboj.builder.renderer import valid_tag


#: **`valid_tag` lives in `modules/naboj/builder/renderer.py`**, and there is one of it.
#:
#: A second copy used to sit here, naming nineteen tags against the authority's ninety-seven --
#: and blessing three spellings the authority records as merged away: `paaa` (now
#: `oblique-throw`), `cog` (now `com`) and `rlc`. It was live code, wired into `ContextNaboj`'s
#: problem schema, and quiet only because `lists.add_numbers` reduces a volume meta's
#: `problems:` to `{id, number}` before a tag ever reaches it. The day somebody wrote a tag in a
#: volume meta, nineteen would have been legal and the other seventy-eight refused.
def building_user():
    """
    Who built this, for the impressum -- and never None.

    `USERNAME` alone was wrong: it is a Windows convention, and on Linux it is set by zsh but not
    by bash, so the build worked or failed depending on the builder's shell. In a container
    neither variable exists and the schema (`'user': And(str, len)`) then rejected None, which is
    how this was found. `getpass.getuser()` consults LOGNAME, USER, LNAME and USERNAME in turn
    and falls back to the password database; it can still raise where there is no entry for the
    uid, which a container run with `--user` is exactly the case for.
    """
    try:
        return getpass.getuser()
    except (KeyError, OSError):
        return os.environ.get('USER') or 'unknown'


class ContextNaboj(FileSystemTreeContext):
    _target = None
    _subdir = None
    #: `modules/naboj/declaration.py` is the one list; this used to be a third, narrower
    #: than the two the command lines accept.
    competitions = declaration.COMPETITIONS
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
        Optional('tags'): [valid_tag],
        Optional('author'): Or([str], []),
        'number': int,
    })
    _schema = Schema({
        'build': {
            'user': And(str, len),
            'dgs': {
                'hash': CommitHash,
                'branch': str,
                'describe': And(str, len),
            },
            'repo': {
                'hash': CommitHash,
                'branch': str,
                'describe': And(str, len),
            },
            'timestamp': datetime.datetime,
        }
    })

    def populate(self, repo_root: str):
        """
        Add the build info to the context. This is useful for impressum and diagnostics
        -   username of whoever built the current context
        -   dgs branch, git hash and `git describe`
        -   repo branch, git hash and `git describe`

        The hash and the description are both kept because they answer different questions.
        The hash is what a machine matches on and is what the PDF's metadata carries; the
        description is what a person quotes, and on a tagged commit it is a name rather than
        a number -- `29-final` instead of `30504fc2`.
        """
        self.add(
            build={
                'user': building_user(),
                'dgs': {
                    'hash': get_last_commit_hash(),
                    'branch': get_branch(),
                    'describe': get_describe(),
                },
                'repo': {
                    'hash': get_last_commit_hash(self.node_path(repo_root)),
                    'branch': get_branch(self.node_path(repo_root)),
                    'describe': get_describe(self.node_path(repo_root)),
                },
                'timestamp': datetime.datetime.now(datetime.UTC),
            },
        )

    def as_tuple(self, competition: str | None = None, volume: int | None = None, sub: str | None = None, issue: str | None = None):
        # Named rather than asserted. A bare `assert` here carried no message, so an
        # unknown competition surfaced as `AssertionError` from inside a constructor; and
        # `python -O` strips it, which would have built the tree for a competition that does
        # not exist. `None` is legal and always was -- the body below is written for it.
        if competition is not None and competition not in self.competitions:
            raise ValueError(f"no such competition: {competition!r} "
                             f"(known: {', '.join(self.competitions)})")

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
