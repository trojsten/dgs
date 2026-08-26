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
            cli = CLIInterface()
            return cli.convertor.run()
        finally:
            sys.argv = saved

    @staticmethod
    def render_collecting(tmp_path, locale, meta, source):
        """As `render`, but hands back the interface so a test can read what it collected."""
        import sys
        from modules.naboj.builder.renderer import CLIInterface
        (tmp_path / 'meta.yaml').write_text(meta)
        src = tmp_path / 'solution.md'
        src.write_text(source)
        out = tmp_path / 'out.md'
        saved = sys.argv
        try:
            sys.argv = ['r', locale, '-C', str(tmp_path / 'meta.yaml'), str(src), str(out)]
            cli = CLIInterface()
            return cli.convertor.run(), cli
        finally:
            sys.argv = saved

    META = (
        "authors:\n  idea: []\n  problem: []\n  solution: []\n"
        "tags: ['kinematics']\n"
        "words:\n"
        "  air:\n"
        "    sk: 'vzduch'\n"
        "    en: 'air'\n"
        "    de: 'Luft'\n"
    )

    def test_a_problem_word_follows_the_language(self, tmp_path):
        source = 'density $\\rho_{\\text{(§ words.air §)}}$\n'
        assert 'vzduch' in self.render(tmp_path, 'sk', self.META, source)
        assert 'air' in self.render(tmp_path, 'en', self.META, source)
        assert 'Luft' in self.render(tmp_path, 'de', self.META, source)

    def test_a_global_word_follows_the_language(self, tmp_path):
        source = "$a \\QQText{(§ i18n.words['and'] §)} b$\n"
        assert '\\QQText{a}' in self.render(tmp_path, 'sk', self.META, source)
        assert '\\QQText{and}' in self.render(tmp_path, 'en', self.META, source)
        assert '\\QQText{und}' in self.render(tmp_path, 'de', self.META, source)

    def test_a_global_word_a_language_lacks_is_boxed_not_guessed(self, tmp_path):
        """
        Never a *silent* fallback. A word inside maths is prose, and falling back means a Slovak
        booklet printing `therefore` -- output that looks right until it is in print. A red box
        does not look right, which is the whole point of using one.
        """
        source = "$a \\QQText{(§ i18n.words['therefore'] §)} b$\n"
        out = self.render(tmp_path, 'sk', self.META, source)
        assert r'\errorMessage{therefore?sk}' in out
        assert 'therefore}' not in out.replace(r'\errorMessage{therefore?sk}', '')

    def test_the_report_names_the_file_to_fix(self, tmp_path):
        source = "$a \\QQText{(§ i18n.words['therefore'] §)} b$\n"
        _, cli = self.render_collecting(tmp_path, 'sk', self.META, source)
        assert 'core/i18n/sk.yaml' in cli.missing_words.report()

    def test_a_missing_problem_word_is_boxed_and_recorded(self, tmp_path):
        """A problem's own word has no English to fall back on, so silence would ship a hole."""
        source = 'density $\\rho_{\\text{(§ words.air §)}}$\n'
        out, cli = self.render_collecting(tmp_path, 'hu', self.META, source)
        assert r'\errorMessage{air?hu}' in out
        assert [t for t, _, _ in cli.missing_words.missing] == ['air']

    def test_a_word_may_be_called_const(self, tmp_path):
        """
        `words.const` shadows nothing -- the reservation is about the top-level namespace, where a
        `values` key called `const` would hide the constants. `22/ht-conundrum` ends its equations
        with `= const` and needs the name.
        """
        meta = ("authors:\n  idea: []\n  problem: []\n  solution: []\n"
                "tags: ['kinematics']\n"
                "words:\n  const:\n    sk: 'konšt'\n    en: 'const'\n")
        source = 'the law $pV = \\text{(§ words.const §)}$\n'
        assert 'konšt' in self.render(tmp_path, 'sk', meta, source)
        assert 'const' in self.render(tmp_path, 'en', meta, source)

    def test_values_still_may_not_be_called_const(self, tmp_path):
        """The top-level reservation stands: there `const` really would shadow the constants."""
        from core.builder.renderer import NameCollisionError
        meta = ("authors:\n  idea: []\n  problem: []\n  solution: []\n"
                "tags: ['kinematics']\nvalues:\n  const: 4\n")
        with pytest.raises(NameCollisionError):
            self.render(tmp_path, 'sk', meta, 'nothing\n')

    def test_one_equation_serves_every_language(self, tmp_path):
        """The point of all this: `eq:` holds the equation once, the words vary."""
        meta = self.META + "eq:\n  drag: '\\rho_{\\text{(§ words.air §)}} v^2 = ma'\n"
        source = "(§ eq.drag|disp('.') §)\n"
        for locale, word in (('sk', 'vzduch'), ('en', 'air'), ('de', 'Luft')):
            out = self.render(tmp_path, locale, meta, source)
            assert f'\\rho_{{\\text{{{word}}}}} v^2 = ma.' in out
            assert '{#eq:' in out


class TestLocalisedI18n:
    """
    `i18n.<word>` reaches the locale's `words:`, so a source can write `(§ i18n.andw §)`
    instead of `(§ i18n.words['and'] §)`.

    `and` and `or` are Jinja keywords -- `(§ i18n.and §)` will not parse -- so those take a
    `w` suffix. Nothing else does.
    """

    @staticmethod
    def make(words, language='sk', data=None):
        from core.builder.renderer import LocalisedI18n, LocalisedWords
        w = LocalisedWords(words, language, f'core/i18n/{language}.yaml')
        return LocalisedI18n(data if data is not None else {'full': 'slovak'}, w)

    def test_keyword_word_takes_the_w_suffix(self):
        assert self.make({'and': 'a'})['andw'] == 'a'

    def test_or_likewise(self):
        assert self.make({'or': 'alebo'})['orw'] == 'alebo'

    def test_a_word_that_is_not_a_keyword_keeps_its_name(self):
        assert self.make({'wherefrom': 'odkiaľ'})['wherefrom'] == 'odkiaľ'

    def test_locale_data_still_wins_and_is_untouched(self):
        """`i18n.full` is the locale's own key, not a word lookup."""
        assert self.make({'and': 'a'})['full'] == 'slovak'

    def test_words_mapping_is_still_reachable(self):
        i18n = self.make({'and': 'a'})
        i18n['words'] = i18n._words
        assert i18n['words']['and'] == 'a'

    def test_missing_word_raises_naming_the_unsuffixed_term(self):
        """`andw` is the spelling; `and` is what the author has to add. Say `and`."""
        from core.builder.renderer import MissingWordError
        with pytest.raises(MissingWordError) as exc:
            _ = self.make({}, language='ru')['andw']
        assert '`and`' in str(exc.value) and 'ru' in str(exc.value)

    def test_a_suffixed_non_keyword_is_not_stripped(self):
        """`nw` must not be read as the word `n`: only keywords carry the suffix rule."""
        from core.builder.renderer import MissingWordError
        with pytest.raises(MissingWordError) as exc:
            _ = self.make({'n': 'en'})['nw']
        assert '`nw`' in str(exc.value)

    def test_a_word_colliding_with_a_locale_key_is_refused(self):
        """Otherwise `i18n.full` would silently return the locale name, not the word."""
        with pytest.raises(ValueError, match='collide'):
            self.make({'full': 'úplný'}, data={'full': 'slovak'})


class TestMissingWordRegistry:
    """
    A missing word is boxed rather than fatal, so the booklet still builds with the hole marked --
    the same call `\\protectedInput` makes for a missing file. The registry is what keeps that from
    being silent: it collects every miss for one report at the end.
    """

    @staticmethod
    def words(mapping, language='ru', registry=None):
        from core.builder.renderer import LocalisedWords
        return LocalisedWords(mapping, language, f'core/i18n/{language}.yaml', registry=registry)

    def test_a_miss_becomes_a_red_box(self):
        from core.builder.renderer import MissingWordRegistry
        reg = MissingWordRegistry()
        assert self.words({}, registry=reg)['and'] == r'\errorMessage{and?ru}'

    def test_the_miss_is_recorded(self):
        from core.builder.renderer import MissingWordRegistry
        reg = MissingWordRegistry()
        _ = self.words({}, registry=reg)['and']
        assert reg.missing == [('and', 'ru', 'core/i18n/ru.yaml')]

    def test_the_same_miss_is_recorded_once(self):
        """An equation reused in six places should not report the same gap six times."""
        from core.builder.renderer import MissingWordRegistry
        reg = MissingWordRegistry()
        w = self.words({}, registry=reg)
        _, _, _ = w['and'], w['and'], w['and']
        assert len(reg.missing) == 1

    def test_a_word_that_is_present_is_not_recorded(self):
        from core.builder.renderer import MissingWordRegistry
        reg = MissingWordRegistry()
        assert self.words({'and': 'a'}, language='sk', registry=reg)['and'] == 'a'
        assert reg.missing == []

    def test_report_is_none_when_nothing_is_missing(self):
        from core.builder.renderer import MissingWordRegistry
        assert MissingWordRegistry().report() is None

    def test_report_names_every_gap(self):
        from core.builder.renderer import MissingWordRegistry
        reg = MissingWordRegistry()
        w = self.words({}, registry=reg)
        _, _ = w['and'], w['therefore']
        report = reg.report()
        assert '`and`' in report and '`therefore`' in report and 'ru' in report

    def test_without_a_registry_it_still_raises(self):
        """Callers outside a render want the failure, not a box they will never look at."""
        from core.builder.renderer import MissingWordError
        with pytest.raises(MissingWordError):
            _ = self.words({})['and']
