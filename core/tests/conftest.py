"""
Fixtures shared by the core suite.

The rule this file exists to keep: **`core/tests/` must pass in a checkout that has no content
repositories.** Nothing under `source/` is tracked -- each module names its own repositories in
`modules/<module>/editor.yaml`, and cloning them is optional -- so a test that needs one is a
test in the wrong place. Those live in `modules/<module>/tests/`, where they skip when the
repository is absent.

What core *may* depend on is core's own build artefacts, which is what the fixture below is for.
"""
import pathlib
import subprocess
import sys

import pytest

from core import i18n

#: Where `build/core/i18n/%.tex` lands, and what reads it: `texmath.py` loads the `.tex` into
#: every formula it sets, and `Convertor` passes the `.yaml` to pandoc-crossref as `crossrefYaml`,
#: which is where `Obrázok`, `Abbildung` and the other nine figure words come from.
I18N = pathlib.Path('build/core/i18n')


@pytest.fixture(scope='session')
def i18n_built():
    """
    `build/core/i18n/` present, built if it is not.

    A test that asks for a caption in Slovak, or sets a formula with xelatex, needs these; make
    builds them from `core/i18n/*.yaml` and `core/templates/`, all of it core's own, so a suite
    run before a build can do the same rather than skip. Without them pandoc-crossref falls back
    to English and `Obrázok 1:` quietly reads `Figure 1:` -- a test failure that looks like a
    broken regex and is a missing file.

    Session-scoped and idempotent: a language already built is left alone, so this costs nothing
    after the first run and nothing at all after a `make`.
    """
    I18N.mkdir(parents=True, exist_ok=True)      # the builder wants an existing output directory
    for language in sorted(i18n.languages):
        if (I18N / f'{language}.tex').is_file() and (I18N / f'{language}.yaml').is_file():
            continue
        done = subprocess.run([sys.executable, '-m', 'core.builder.i18n',
                               'core/i18n/', 'core/templates/', language, '-o', str(I18N)],
                              capture_output=True, text=True)
        if done.returncode:
            # not `check=True`: that reports the exit status and swallows the one line saying why
            raise RuntimeError(f'could not build build/core/i18n/{language}: '
                               f'{done.stderr.strip() or done.stdout.strip()}')
    return I18N
