"""
The editor's capability probe, and the TeX target it exposes.

Everything here runs without pandoc, xelatex or make: the probe's job is to *report* what is
missing, so the tests feed it a fake environment rather than the machine's real one. That is also
why these live outside `tools/` -- `pytest.ini` collects `core/tests/`, and a probe that only
worked on a fully installed machine would be exactly the thing this change exists to remove.
"""
import pathlib
import sys

import pytest
import yaml

EDITOR = pathlib.Path(__file__).resolve().parents[2] / 'tools' / 'editor'
sys.path.insert(0, str(EDITOR))

import capabilities                                   # noqa: E402
from descriptors import UnitKind, declared_sources, describe_source   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _clear_cache():
    """The probe memoises for the life of the process; a test must not see another's answer."""
    capabilities._CACHE['payload'] = None
    yield
    capabilities._CACHE['payload'] = None


class TestTheTexTargetIsDerived:
    """
    `tex` is not written out per descriptor -- it is `render` with the prefix and the extension
    swapped, which is the relation every `module.mk` encodes. These pin that it stays true.
    """

    def test_it_swaps_the_prefix_and_the_extension(self):
        kind = UnitKind(glob='*', render='render/naboj/{unit}/{language}/{target}.md')
        assert kind.tex == 'build/naboj/{unit}/{language}/{target}.tex'

    def test_an_override_wins(self):
        kind = UnitKind(glob='*', render='render/x/{target}.md', tex_override='build/odd.tex')
        assert kind.tex == 'build/odd.tex'

    def test_a_module_with_no_render_rule_has_no_tex_rule(self):
        assert UnitKind(glob='*').tex == ''

    def test_something_that_is_not_a_render_target_is_refused(self):
        """Better no TeX tab than a target make has no rule for."""
        assert UnitKind(glob='*', render='output/naboj/{unit}.pdf').tex == ''

    @pytest.mark.parametrize('descriptor', sorted(ROOT.glob('modules/*/editor.yaml')))
    def test_every_real_descriptor_yields_a_rule_module_mk_has(self, descriptor):
        """The derived target must name a rule that actually exists in the module's makefile."""
        spec = yaml.safe_load(descriptor.read_text()) or {}
        module = descriptor.parent.name
        makefile = (descriptor.parent / 'module.mk').read_text()
        for entry in spec.get('units') or []:
            kind = UnitKind(glob=entry['glob'], render=entry.get('render', ''),
                            tex_override=entry.get('tex', ''))
            if not kind.tex:
                continue
            assert kind.tex.startswith(f'build/{module}/')
            assert kind.tex.endswith('.tex')
            # module.mk writes the rule head with `%` where the descriptor writes `{unit}`
            assert f'build/{module}/%' in makefile


class TestTiersDegradeInOrder:
    """A tier is never usable when the one below it is not, whatever its own tools report."""

    def _payload(self, monkeypatch, *, present):
        monkeypatch.setattr(capabilities, '_which', lambda name: '/usr/bin/' + name
                            if name in present else '')

        def fake_run(argv, *, stdin=None, timeout=30):
            tool = argv[0]
            # kpsewhich is the lookup tool, not a capability: what matters is what it finds.
            if tool == 'kpsewhich':
                return (0, f'/texmf/{argv[1]}\n') if argv[1] in present else (1, '')
            if tool not in present:
                return None
            if tool == 'make':
                return 0, 'GNU Make 4.4\n'
            if tool == 'pandoc':
                if stdin is None:                      # `pandoc --version`
                    return 0, 'pandoc 3.10.1\n'
                if 'pandoc-crossref' in present:       # the functional filter probe
                    return 0, 'x ref{eq:d}\n'
                return 1, 'Error running filter pandoc-crossref\n'
            return 0, ''
        monkeypatch.setattr(capabilities, '_run', fake_run)
        return capabilities.capabilities(ROOT, refresh=True)

    def tiers(self, payload):
        return {t['id']: t['ok'] for t in payload['tiers']}

    def test_markdown_alone_needs_no_pandoc_and_no_latex(self, monkeypatch):
        payload = self._payload(monkeypatch, present={'make', 'uv'})
        assert self.tiers(payload) == {
            'markdown': True, 'tex': False, 'latex': False, 'pdf': False}

    def test_no_make_takes_every_pipeline_tier_with_it(self, monkeypatch):
        payload = self._payload(monkeypatch, present={'pandoc', 'pandoc-crossref', 'xelatex'})
        tiers = self.tiers(payload)
        assert tiers['markdown'] is False
        assert tiers['tex'] is False
        assert tiers['pdf'] is False

    def test_the_macro_sweep_does_not_need_pandoc(self, monkeypatch):
        """
        `latex` is what the macro sweep needs: it writes its own probe document and hands it
        straight to xelatex, so a machine with TeX but no pandoc can still run it.
        """
        payload = self._payload(monkeypatch, present={
            'make', 'uv', 'xelatex', 'texfot', 'dgs.cls', 'MinionPro.sty'})
        tiers = self.tiers(payload)
        assert tiers['latex'] is True
        assert tiers['tex'] is False        # no pandoc
        assert tiers['pdf'] is False

    def test_xelatex_without_the_class_is_not_a_pdf(self, monkeypatch):
        """`which xelatex` is not enough: dgs.cls and MinionPro.sty decide it."""
        payload = self._payload(monkeypatch, present={
            'make', 'uv', 'pandoc', 'pandoc-crossref', 'xelatex', 'texfot'})
        assert self.tiers(payload)['tex'] is True
        assert self.tiers(payload)['pdf'] is False

    def test_a_missing_tier_carries_a_reason_and_a_command(self, monkeypatch):
        payload = self._payload(monkeypatch, present={'make', 'uv'})
        tex = next(t for t in payload['tiers'] if t['id'] == 'tex')
        assert tex['reason']
        assert any('install-pandoc' in line for line in tex['install'])

    def test_the_install_hint_is_not_repeated(self, monkeypatch):
        """pandoc and its filter share one script; saying it twice reads like two steps."""
        payload = self._payload(monkeypatch, present={'make', 'uv'})
        tex = next(t for t in payload['tiers'] if t['id'] == 'tex')
        assert len(tex['install']) == len(set(tex['install']))


class TestTheLauncherDoesNotNeedUv:
    def test_uv_is_used_when_it_is_there(self, monkeypatch):
        monkeypatch.setattr(capabilities, '_which', lambda name: '/usr/bin/uv' if name == 'uv' else '')
        assert capabilities.probe_python_launcher()['argv'] == ['uv', 'run', 'make']

    def test_without_uv_it_falls_back_to_the_running_interpreter(self, monkeypatch):
        monkeypatch.setattr(capabilities, '_which', lambda name: '')
        launcher = capabilities.probe_python_launcher()
        assert launcher['argv'] == ['make']
        # the venv's bin directory, not the base interpreter it symlinks to
        assert launcher['path_prefix'] == str(pathlib.Path(sys.executable).parent)


class TestDescribeSourceExplainsAnEmptyClone:
    def test_the_descriptor_declares_where_the_content_comes_from(self):
        """
        Nothing under `source/` is a submodule, so `.gitmodules` never described it honestly and
        no longer lists it. The module's own descriptor does.
        """
        declared = declared_sources(ROOT)
        assert 'naboj' in declared
        assert any(e['path'] == 'source/naboj/phys' for e in declared['naboj'])
        assert all(e['url'] for e in declared['naboj'])

    def test_a_tree_with_no_sources_is_reported_as_empty(self, tmp_path):
        (tmp_path / 'modules' / 'naboj').mkdir(parents=True)
        (tmp_path / 'modules' / 'naboj' / 'editor.yaml').write_text(
            'label: Náboj\nunits:\n  - glob: "*/*/problems/*"\n')
        described = describe_source(tmp_path)
        assert described['empty'] is True
        assert described['modules'][0]['present'] is False
        assert 'not submodules' in described['note']

    def test_a_populated_checkout_is_not_reported_as_empty(self):
        """
        The other direction, on a real tree. Skipped where there is no tree: inside the container
        image `source/` is deliberately empty -- it is 657 MB of separate private repositories,
        bind-mounted at run time -- and `empty: True` is the correct answer there, not a failure.
        """
        if not (ROOT / 'source').is_dir():
            pytest.skip('no source/ here; this is how it looks inside the image')
        assert describe_source(ROOT)['empty'] is False
