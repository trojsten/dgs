import pytest

from core.builder.renderer import JinjaConvertor


def make_convertor(preamble):
    convertor = JinjaConvertor.__new__(JinjaConvertor)
    convertor.preamble = preamble
    return convertor


class TestPrepareTemplate:
    def test_no_preamble(self):
        assert make_convertor(None).prepare_template("body") == "body"

    def test_empty_preamble(self):
        assert make_convertor("").prepare_template("body") == "body"

    def test_whitespace_only_preamble(self):
        assert make_convertor("   \n\n").prepare_template("body") == "body"

    def test_single_trailing_newline(self):
        assert make_convertor("@J set x = 1\n").prepare_template("body") == "@J set x = 1\nbody"

    def test_multiple_trailing_newlines_collapse_to_one(self):
        assert make_convertor("@J set x = 1\n\n\n").prepare_template("body") == "@J set x = 1\nbody"

    def test_no_trailing_newline_still_gets_one(self):
        assert make_convertor("@J set x = 1").prepare_template("body") == "@J set x = 1\nbody"


class TestTranslatedWords:
    """
    Words that live inside maths and have to change with the language.

    Two tiers, because the vocabulary splits cleanly. `and`, `or` and their kind recur everywhere and
    live in `core/i18n`; a term like `air` or `impact` appears in one problem and lives in its meta --
    of the 190 words found inside `\\text{}` across phys, 167 occur in exactly one problem.

    Both exist so one `eq:` entry can serve every language. Before this the Markdown stage never
    learned which language it was rendering, so a translated subscript meant a separate copy of the
    equation per language, and the copies drifted.
    """

    @staticmethod
    def render(tmp_path, locale, meta, source):
        import sys
        from modules.naboj.builder.renderer import CLIInterface
        (tmp_path / 'meta.yaml').write_text(meta)
        src = tmp_path / 'solution.md'
        src.write_text(source)
        out = tmp_path / 'out.md'
        saved = sys.argv
        try:
            sys.argv = ['r', locale, '-C', str(tmp_path / 'meta.yaml'), str(src), str(out)]
            return CLIInterface().convertor.run()
        finally:
            sys.argv = saved

    META = ("authors:\n  idea: []\n  problem: []\n  solution: []\ntags: ['kinematics']\n"
            "words:\n  air: {sk: 'vzduch', en: 'air', de: 'Luft'}\n")

    def test_a_problem_word_follows_the_language(self, tmp_path):
        source = 'density $\\rho_{\\text{(§ w.air §)}}$\n'
        assert 'vzduch' in self.render(tmp_path, 'sk', self.META, source)
        assert 'air' in self.render(tmp_path, 'en', self.META, source)
        assert 'Luft' in self.render(tmp_path, 'de', self.META, source)

    def test_a_global_word_follows_the_language(self, tmp_path):
        source = "$a \\QQText{(§ i18n.words['and'] §)} b$\n"
        assert '\\QQText{a}' in self.render(tmp_path, 'sk', self.META, source)
        assert '\\QQText{and}' in self.render(tmp_path, 'en', self.META, source)
        assert '\\QQText{und}' in self.render(tmp_path, 'de', self.META, source)

    def test_a_language_with_no_translation_falls_back_to_english(self, tmp_path):
        """`therefore` is filled in nowhere yet; a build must not fail over that."""
        source = "$a \\QQText{(§ i18n.words['therefore'] §)} b$\n"
        assert '\\QQText{therefore}' in self.render(tmp_path, 'sk', self.META, source)

    def test_a_missing_problem_word_is_an_error(self, tmp_path):
        """A problem's own word has no English to fall back on, so silence would ship a hole."""
        from core.builder.renderer import MissingWordError
        source = 'density $\\rho_{\\text{(§ w.air §)}}$\n'
        with pytest.raises(MissingWordError, match='no hu translation'):
            self.render(tmp_path, 'hu', self.META, source)

    def test_one_equation_serves_every_language(self, tmp_path):
        """The point of all this: `eq:` holds the equation once, the words vary."""
        meta = self.META + "eq:\n  drag: '\\rho_{\\text{(§ w.air §)}} v^2 = ma'\n"
        source = "(§ eq.drag|disp('.') §)\n"
        for locale, word in (('sk', 'vzduch'), ('en', 'air'), ('de', 'Luft')):
            out = self.render(tmp_path, locale, meta, source)
            assert f'\\rho_{{\\text{{{word}}}}} v^2 = ma.' in out
            assert '{#eq:' in out
