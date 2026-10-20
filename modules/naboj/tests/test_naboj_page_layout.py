r"""
What `modules/naboj/editor.yaml` promises the rest of the build, asserted against the real file.

This lives here and not in `core/tests/` because it needs `source/naboj/` to be checked out:
`descriptors.load_modules` knows a module only when its content repository is populated, and the
content repositories are optional -- a checkout with none of them still has to run the core
suite green. So the module-agnostic behaviour of `core/html/page.py` is tested in core against a
stub descriptor, and the claims about *this* module are tested here, where they belong and where
they are skipped when there is nothing to make them about.
"""
import pathlib

import pytest

from core.html import page

pytestmark = pytest.mark.skipif(not pathlib.Path('source/naboj').is_dir(),
                                reason='source/naboj is not checked out')


class TestTheDescriptor:
    def test_naboj_has_a_language_directory(self):
        """
        `languages: true`, which is the one module that carries it. A problem holds a directory
        per language, so a fragment is `<problem>/<lang>/solution.html`; guessing that by looking
        would make a half-built Náboj problem look like a monolingual one.
        """
        languages, targets = page.describe('naboj')
        assert languages
        assert targets[:2] == ['problem', 'problem-extra']

    def test_a_language_directory_is_where_a_fragment_is_looked_for(self, tmp_path):
        """
        The quiet half: the same directory read as Náboj's, with nothing in the language
        directory, finds nothing rather than falling back to what lies beside it. Were it to
        fall back, a problem whose language directory was missing would silently assemble from
        another language's fragments.
        """
        problem = tmp_path / 'unit'
        problem.mkdir()
        (problem / 'problem.html').write_text('<p>Vedľa, nie vnútri.</p>')
        with pytest.raises(FileNotFoundError, match='sk'):
            page.build(problem, 'sk', tmp_path / 'out', engine='latex', module='naboj')
