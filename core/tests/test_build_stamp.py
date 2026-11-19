r"""
What a document says about the tree it was built from.

`get_describe` is one `git describe` away from the shell, and it would not be worth a test
except that two documents print what it returns -- the colophon on a booklet's last page and
the `pdfkeywords` of every Náboj PDF -- and the whole point of a build stamp is that it cannot
quietly say something that is not so. The two cases that matter are the ones git is silent
about: a repository with no tags at all, and a tree that has been edited since its last commit.

It runs against this repository, which is a git checkout like any other; `--always` is what
makes it work in one that has never been tagged, so there is nothing here that a fresh clone
cannot answer.
"""
import pathlib
import re
import subprocess

import pytest

from core.builder.builder import get_describe, get_last_commit_hash

REPO = pathlib.Path(__file__).resolve().parents[2]


def dirty(cwd: pathlib.Path) -> bool:
    return bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=cwd).strip())


class TestTheVersionADocumentPrints:
    def test_it_says_something(self):
        assert get_describe(REPO)

    def test_it_is_one_token(self):
        """It goes into a `\\texttt{}` on a page and into a `key=value` in the PDF keywords."""
        assert not re.search(r'\s', get_describe(REPO))

    def test_it_names_the_commit_or_a_tag_of_it(self):
        """
        Either the short hash outright, or a tag with the hash after a `-g`, or a bare tag on a
        commit that is exactly one. The first two are what a reader checks out by hand.
        """
        describe, commit = get_describe(REPO), get_last_commit_hash(REPO)
        tagged = subprocess.run(['git', 'describe', '--tags', '--exact-match'],
                                cwd=REPO, capture_output=True).returncode == 0
        assert tagged or commit in describe

    def test_it_admits_an_edited_tree(self):
        """
        The one thing a stamp must not do is name a tree that was never built. A hash taken
        from a dirty checkout does exactly that, which is why `--dirty` is not optional.
        """
        assert get_describe(REPO).endswith('-dirty') == dirty(REPO)

    def test_a_clean_tree_is_not_marked(self, tmp_path):
        """The quiet half: the suffix means something only if it is absent the rest of the time."""
        subprocess.run(['git', 'init', '-q'], cwd=tmp_path, check=True)
        subprocess.run(['git', 'config', 'user.email', 't@t'], cwd=tmp_path, check=True)
        subprocess.run(['git', 'config', 'user.name', 'T'], cwd=tmp_path, check=True)
        (tmp_path / 'a').write_text('a')
        subprocess.run(['git', 'add', 'a'], cwd=tmp_path, check=True)
        subprocess.run(['git', 'commit', '-qm', 'a'], cwd=tmp_path, check=True)
        assert not get_describe(tmp_path).endswith('-dirty')

        (tmp_path / 'a').write_text('b')
        assert get_describe(tmp_path).endswith('-dirty')

    def test_a_tag_wins_over_the_hash(self, tmp_path):
        """`29-final` is a lightweight tag, so `--tags` is what makes it count at all."""
        subprocess.run(['git', 'init', '-q'], cwd=tmp_path, check=True)
        subprocess.run(['git', 'config', 'user.email', 't@t'], cwd=tmp_path, check=True)
        subprocess.run(['git', 'config', 'user.name', 'T'], cwd=tmp_path, check=True)
        (tmp_path / 'a').write_text('a')
        subprocess.run(['git', 'add', 'a'], cwd=tmp_path, check=True)
        subprocess.run(['git', 'commit', '-qm', 'a'], cwd=tmp_path, check=True)
        assert get_describe(tmp_path) == get_last_commit_hash(tmp_path)

        subprocess.run(['git', 'tag', '29-final'], cwd=tmp_path, check=True)
        assert get_describe(tmp_path) == '29-final'


class TestTheNabojBuildContext:
    """The schema is what stops a document printing an empty version slot."""

    @pytest.fixture
    def schema(self):
        from modules.naboj.builder.contexts.base import ContextNaboj
        return ContextNaboj._schema

    def test_both_repositories_declare_a_description(self, schema):
        for repo in ('dgs', 'repo'):
            assert 'describe' in schema.schema['build'][repo]
