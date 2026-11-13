import pytest

from core.builder import words
from core.builder.context.context import DuplicateKeyError


def problem(tmp_path, **per_language):
    """A problem directory with a `words.yaml` in each language given."""
    for locale, text in per_language.items():
        (tmp_path / locale).mkdir(exist_ok=True)
        (tmp_path / locale / 'words.yaml').write_text(text)
    return tmp_path


class TestWhereTheFileIs:
    """
    The lookup is keyed off the **locale**, never off the directory of the file being rendered.

    That is the whole reason it works: `18/bathmobile/answer.md` sits at the problem root, because
    an answer in volumes `14`-`18` is a value and needs no translated copy, and it is still
    rendered once per language. A rule of "beside the file" finds nothing for it in any language.
    """

    def test_it_is_under_the_locale(self, tmp_path):
        problem(tmp_path, sk="air: 'vzduch'\n")
        assert words.path_for(tmp_path, 'sk') == tmp_path / 'sk' / 'words.yaml'

    def test_a_locale_with_no_directory_falls_back_to_the_root(self, tmp_path):
        """
        Which is how a monolingual module would spell it -- seminar and scholar hold no language
        directories at all. Nothing uses it today; it is defined so the fallback is not a surprise.
        """
        assert words.path_for(tmp_path, 'sk') == tmp_path / 'words.yaml'
        assert words.path_for(tmp_path, '') == tmp_path / 'words.yaml'


class TestLoading:
    def test_a_flat_file_is_the_language_itself(self, tmp_path):
        """No language key inside: the directory already says which language this is."""
        problem(tmp_path, sk="air: 'vzduch'\ntwin: 's'\n")
        assert words.load(tmp_path, 'sk') == {'air': 'vzduch', 'twin': 's'}

    def test_an_absent_file_is_empty_and_not_an_error(self, tmp_path):
        """
        A problem with no words has no file in any language, and a language that needs none has
        none of its own. What makes a word *required* is a template asking for it.
        """
        assert words.load(tmp_path, 'sk') == {}

    def test_an_empty_file_is_empty(self, tmp_path):
        problem(tmp_path, sk='')
        assert words.load(tmp_path, 'sk') == {}

    @pytest.mark.parametrize('value, expected', [
        ("forsome: ' for some '\n", ' for some '),
        ("water: '\\varrho'\n", '\\varrho'),
        ("escape: '{\\text{sz}}'\n", '{\\text{sz}}'),
    ])
    def test_the_awkward_values_survive(self, tmp_path, value, expected):
        """
        Three shapes the corpus actually holds, and each would be lost by a careless writer: a
        phrase whose surrounding spaces are the point (`26/under-tension`), and two values that
        are TeX rather than words (`27/irrigation`, `21/angry-planet`).
        """
        problem(tmp_path, sk=value)
        assert list(words.load(tmp_path, 'sk').values()) == [expected]


class TestWhatIsRefused:
    """Loud rather than skipped: an unreadable file and an absent one must not look alike."""

    def test_a_nested_value_is_refused(self, tmp_path):
        """The old shape. `sk: {en: ...}` inside `sk/words.yaml` reads fine and means nothing."""
        problem(tmp_path, sk="air:\n  en: 'air'\n")
        with pytest.raises(words.WordsFileError):
            words.load(tmp_path, 'sk')

    def test_a_term_that_is_not_an_identifier_is_refused(self, tmp_path):
        problem(tmp_path, sk="not-an-identifier: 'x'\n")
        with pytest.raises(words.WordsFileError):
            words.load(tmp_path, 'sk')

    def test_a_file_that_is_not_a_mapping_is_refused(self, tmp_path):
        problem(tmp_path, sk="- air\n- water\n")
        with pytest.raises(words.WordsFileError, match='not a mapping'):
            words.load(tmp_path, 'sk')

    def test_broken_yaml_is_refused_naming_the_file(self, tmp_path):
        problem(tmp_path, sk="air: 'vzduch\n  bad: [\n")
        with pytest.raises(words.WordsFileError) as caught:
            words.load(tmp_path, 'sk')
        assert 'sk/words.yaml' in str(caught.value)

    def test_a_duplicate_term_is_refused(self, tmp_path):
        """
        PyYAML keeps the last value at the first key's position, which is invisible in a diff.
        `UniqueKeyLoader` is the repository's answer to that and this file gets it too.
        """
        problem(tmp_path, sk="air: 'vzduch'\nair: 'luft'\n")
        with pytest.raises(DuplicateKeyError):
            words.load(tmp_path, 'sk')


class TestTheRowView:
    """
    The one thing splitting the block cost, rebuilt: every language of a term on one line.

    `21/pool-jump` is why it is worth rebuilding. Slovak and Czech wrote the twin's density as
    `\\rho_s` and English and Hungarian as `\\rho_t`, while the shared equation all four rendered
    printed `\\rho_s` -- so the English booklet introduced one symbol and solved with another.
    Four values side by side is what makes that visible; four files do not.
    """

    def test_it_puts_every_language_on_one_term(self, tmp_path):
        problem(tmp_path, sk="twin: 's'\n", cs="twin: 's'\n",
                en="twin: 't'\n", hu="twin: 't'\n")
        assert words.rows(tmp_path) == {'twin': {'sk': 's', 'cs': 's', 'en': 't', 'hu': 't'}}

    def test_a_term_only_one_language_has_is_still_a_row(self, tmp_path):
        """That is usually the gap, not a term belonging to one reader. `word-missing` decides."""
        problem(tmp_path, sk="air: 'vzduch'\nonly: 'x'\n", en="air: 'air'\n")
        assert words.rows(tmp_path) == {'air': {'sk': 'vzduch', 'en': 'air'},
                                        'only': {'sk': 'x'}}

    def test_a_problem_with_no_words_has_no_rows(self, tmp_path):
        (tmp_path / 'sk').mkdir()
        assert words.rows(tmp_path) == {}
        assert words.languages(tmp_path) == []

    def test_a_directory_that_is_not_a_language_is_not_one(self, tmp_path):
        """Two letters and alphabetic, the same rule `core/audit/sources.py` reads."""
        for name in ('sk', 'pictures', 'e', '00'):
            (tmp_path / name).mkdir()
            (tmp_path / name / 'words.yaml').write_text("air: 'x'\n")
        assert words.languages(tmp_path) == ['sk']

    def test_invert_is_the_same_turn_without_reading_again(self, tmp_path):
        """
        What the audit calls: it has already read every file into `Unit.words`, and reading them
        a second time to turn them round is the one thing `core/audit/sources.py` exists to avoid.
        """
        problem(tmp_path, sk="twin: 's'\n", en="twin: 't'\n")
        assert words.invert({'sk': {'twin': 's'}, 'en': {'twin': 't'}}) == words.rows(tmp_path)
