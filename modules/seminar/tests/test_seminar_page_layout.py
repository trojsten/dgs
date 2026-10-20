r"""
What `modules/seminar/editor.yaml` promises, asserted against the real file.

Here rather than in `core/tests/` for the reason given in `modules/naboj/tests/`: it needs
`source/seminar/` checked out, and a checkout without the content repositories still has to run
the core suite green.
"""
import pathlib

import pytest

from core.html import page

pytestmark = pytest.mark.skipif(not pathlib.Path('source/seminar').is_dir(),
                                reason='source/seminar is not checked out')


class TestTheDescriptor:
    def test_seminar_is_monolingual(self):
        """
        No `languages:` key, deliberately: seminar has **one** language, not one of several that
        happens to be checked out, so its fragments sit in the problem directory itself.
        """
        languages, targets = page.describe('seminar')
        assert not languages
        assert targets == ['problem', 'solution']

    def test_a_unit_assembles_from_the_problem_directory(self, tmp_path):
        """The other side of the same fact, through `build` rather than through the descriptor."""
        problem = tmp_path / 'unit'
        problem.mkdir()
        (problem / 'problem.html').write_text('<p>Rýchlosť vlaku.</p>')
        out = page.build(problem, 'sk', tmp_path / 'out', files=('problem',),
                         engine='mathjax', module='seminar')
        assert 'Rýchlosť vlaku' in out.read_text()
