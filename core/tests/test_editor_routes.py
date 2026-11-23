r"""
The editor's routes, against a module root built here rather than a content repository.

`tools/editor/app.py` is 1300 lines and 22 routes, and before this two of them were touched by
any test -- `GET /` for smoke, and `/api/evaluate`, whose file is `skipif`'d on a real Náboj
problem and therefore contributes nothing in a checkout with no content. Under this repository's
own rule, that is zero coverage of the one web application it ships.

What is pinned here is the part where a mistake is not a wrong page but a wrong *file*: which
paths a request may reach, and what `/api/save` -- the only route that writes into the source
tree -- refuses to do. Every one of these runs with no content checked out, which is what lets
them live in `core/tests/`.

**The fixture builds a module rather than mocking one.** A descriptor, a source tree and the
real `discover_units` walking it, so the thing under test is the resolution the editor actually
performs. `MODULES` is populated at import from the real repository, so it is replaced wholesale
-- that import-time global is itself why this file needs a fixture rather than a `tmp_path`.
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'tools' / 'editor'))

import app                                                              # noqa: E402
from descriptors import Module, UnitKind                                # noqa: E402

DESCRIPTOR = UnitKind(
    glob='*/*/problems/*',
    levels=('competition', 'volume', 'kind', 'problem'),
    targets=('problem', 'solution', 'answer'),
    translated=('problem', 'solution'),
    render='render/widget/{unit}/{language}/{target}.md',
    preview='output/widget/{unit}/{language}/standalone.pdf',
)


@pytest.fixture
def editor(tmp_path, monkeypatch):
    """A client, a repository root and one unit in it: `comp/01/problems/thing`, in `sk`."""
    root = tmp_path / 'source' / 'widget'
    unit = root / 'comp' / '01' / 'problems' / 'thing'
    (unit / 'sk').mkdir(parents=True)
    (unit / 'sk' / 'problem.md').write_text('a problem\n')
    (unit / 'sk' / 'solution.md').write_text('a solution\n')
    (unit / 'meta.yaml').write_text('id: thing\n')
    (tmp_path / 'output').mkdir()
    (tmp_path / 'output' / 'visible.svg').write_text('<svg/>')
    (tmp_path / 'secret.txt').write_text('not ours to serve\n')

    module = Module(name='widget', label='Widget', languages=True, kinds=(DESCRIPTOR,),
                    root=root, scope='volume', audit=False)
    monkeypatch.setattr(app, 'MODULES', {'widget': module})
    monkeypatch.setattr(app, 'REPO_ROOT', tmp_path)
    app.app.config.update(TESTING=True)
    return app.app.test_client(), tmp_path, unit


def post(client, route, **body):
    return client.post(route, data=json.dumps(body), content_type='application/json')


class TestWhatASaveRefuses:
    """
    `/api/save` is the only route that writes into `source/`, and the only guard it had was
    `write_files`' refusal to create a file that does not exist. Nothing tested that either.
    """

    def test_it_writes_a_file_that_is_there(self, editor):
        client, _repo, unit = editor
        response = post(client, '/api/save', module='widget', unit='comp/01/problems/thing',
                        lang='sk', files={'targets': {'problem': 'edited\n'}})
        assert response.status_code == 200
        assert (unit / 'sk' / 'problem.md').read_text() == 'edited\n'

    def test_it_refuses_to_create_one_that_is_not(self, editor):
        """
        An editor edits; it does not conjure files. A typo'd target would otherwise write a
        plausible-looking `answer.md` that no build has ever heard of.
        """
        client, _repo, unit = editor
        response = post(client, '/api/save', module='widget', unit='comp/01/problems/thing',
                        lang='sk', files={'targets': {'answer': 'invented\n'}})
        assert response.status_code == 400
        assert 'Refusing to create' in response.get_json()['error']
        assert not (unit / 'answer.md').exists()

    def test_it_refuses_an_unknown_module(self, editor):
        client, _repo, _unit = editor
        assert post(client, '/api/save', module='elsewhere', unit='x',
                    lang='sk', files={}).status_code == 400

    def test_it_refuses_a_unit_outside_the_module(self, editor):
        """
        Traversal, settled by **membership**: a unit is resolved by looking it up in the set
        `discover_units` found, so `../` is simply not a key. This is what says so.
        """
        client, _repo, _unit = editor
        for escape in ('../../../etc', 'comp/01/problems/../../../..', '/etc'):
            response = post(client, '/api/save', module='widget', unit=escape,
                            lang='sk', files={})
            assert response.status_code == 400, escape

    def test_it_refuses_a_language_that_is_not_there(self, editor):
        client, _repo, _unit = editor
        for bad in ('../..', 'zz', 'sk/../../..'):
            response = post(client, '/api/save', module='widget',
                            unit='comp/01/problems/thing', lang=bad,
                            files={'targets': {'problem': 'x\n'}})
            assert response.status_code == 400, bad

    def test_it_will_not_write_through_a_symlink(self, editor):
        """
        The route-level half of `write_through`. 84 translations under `source/` are symlinks,
        so this is the ordinary case rather than an attack: saving the Polish tab used to
        rewrite the English source.
        """
        client, _repo, unit = editor
        master = unit / 'sk' / 'solution.md'
        (unit / 'cs').mkdir()
        (unit / 'cs' / 'problem.md').write_text('x\n')
        mirror = unit / 'cs' / 'solution.md'
        mirror.symlink_to(master)

        response = post(client, '/api/save', module='widget', unit='comp/01/problems/thing',
                        lang='cs', files={'targets': {'solution': 'written through\n'}})
        assert response.status_code == 400
        assert master.read_text() == 'a solution\n'


class TestWhatTheFileRoutesServe:
    """
    `/api/output` resolves then requires the result to stay under `output/`. The order is what
    makes it symlink-safe, and nothing pinned it.
    """

    def test_a_file_under_output_is_served(self, editor):
        client, _repo, _unit = editor
        assert client.get('/api/output/visible.svg').status_code == 200

    @pytest.mark.parametrize('escape', ['../secret.txt', '../../etc/passwd',
                                        'a/../../secret.txt'])
    def test_a_path_leaving_output_is_refused(self, editor, escape):
        client, _repo, _unit = editor
        assert client.get(f'/api/output/{escape}').status_code == 400

    def test_a_symlink_out_of_output_is_refused(self, editor):
        """
        Resolve *then* compare, which is why the link does not help: a check on the string
        before resolution would pass this.
        """
        client, repo, _unit = editor
        (repo / 'output' / 'escape.txt').symlink_to(repo / 'secret.txt')
        assert client.get('/api/output/escape.txt').status_code == 400


class TestTheCrossOriginGuard:
    """
    Every route acts with the authority of whoever started the server, and there is no login for
    a cross-site request to ride on -- so the browser's own rules are the defence, and this is
    what keeps us out of their way.
    """

    def test_a_foreign_origin_is_refused(self, editor):
        client, _repo, _unit = editor
        response = client.post('/api/save', data='{}', content_type='application/json',
                               headers={'Origin': 'http://evil.example'})
        assert response.status_code == 403

    def test_our_own_origin_is_allowed_through(self, editor):
        """
        The quiet case. The editor's own page sends an `Origin`, and refusing that would refuse
        every real request.
        """
        client, _repo, _unit = editor
        response = client.post('/api/save', data=json.dumps(
            {'module': 'widget', 'unit': 'comp/01/problems/thing', 'lang': 'sk', 'files': {}}),
            content_type='application/json', headers={'Origin': 'http://localhost'})
        assert response.status_code != 403

    def test_a_request_with_no_origin_is_allowed_through(self, editor):
        """`curl`, and the same-origin requests browsers send without one."""
        client, _repo, _unit = editor
        assert post(client, '/api/save', module='widget', unit='comp/01/problems/thing',
                    lang='sk', files={}).status_code == 200

    def test_a_body_that_is_not_json_is_refused(self, editor):
        """
        What `force=True` used to allow. `text/plain` is a *simple* content type, so a
        cross-origin POST of one is sent without a preflight -- and used to be parsed anyway.
        """
        client, _repo, _unit = editor
        response = client.post('/api/save', data=json.dumps({'module': 'widget'}),
                               content_type='text/plain')
        assert response.status_code >= 400
