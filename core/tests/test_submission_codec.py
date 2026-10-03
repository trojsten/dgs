"""
`submission.js`: the block of letters and digits an interactive problem is handed in as.

Tested through its own JavaScript under QuickJS, the way `test_editor_highlight.py` tests the
editor's highlighter and for the same reason -- the file is pure, so the shipped code is what runs
here rather than a Python transcription of it. It matters more than usual: this codec is the only
thing between a participant's afternoon and an evaluator's screen, and a decoder that quietly
returns the *wrong* state is worse than one that refuses.

The file is written out by hand rather than taken from the browser's `btoa` precisely so that
these tests exercise the shipped path. QuickJS has no `btoa`.
"""
import json
import pathlib

import pytest

quickjs = pytest.importorskip('quickjs')

SUBMISSION_JS = pathlib.Path('source/seminar/FKS/.static/web/submission.js')

pytestmark = pytest.mark.skipif(not SUBMISSION_JS.is_file(),
                                reason='source/seminar/FKS is not checked out')


@pytest.fixture(scope='module')
def js():
    """The shipped file, loaded once; everything below is called out of this one context."""
    context = quickjs.Context()
    context.eval(SUBMISSION_JS.read_text())
    return context


@pytest.fixture(scope='module')
def call(js):
    """
    Run an expression and bring the answer back through JSON.

    Through `JSON.stringify`, because quickjs hands an array or an object back as an opaque thing
    with no Python protocol -- the string is the only shape that crosses the boundary intact.
    """
    def run(expression):
        return json.loads(js.eval(f'JSON.stringify({expression})'))
    return run


@pytest.fixture(scope='module')
def roundtrip(js):
    """Encode a list of bytes as a `spectre` body, decode it, and give back what came out."""
    js.eval('''
        makeBlob = function (app, task, values) {
            return Submission.encode(app, task, w => w.bytes8(values));
        };
        readBlob = function (text, app, n) {
            const d = Submission.decode(text, app);
            return { format: d.format, app: d.app, task: d.task, body: [...d.reader.bytes8(n)] };
        };
        failure = function (text, app, n) {
            try { readBlob(text, app, n); return null; } catch (e) { return e.code; }
        };
    ''')
    return None


BODY = [0, 1, 127, 128, 254, 255, 42]


class TestItComesBackTheSameWayItWentIn:
    def test_a_body_survives(self, js, call, roundtrip):
        blob = js.eval(f'makeBlob("spectre", 4, {BODY})')
        assert call(f'readBlob({blob!r}, "spectre", {len(BODY)})') == {
            'format': 1, 'app': 1, 'task': 4, 'body': BODY}

    def test_every_byte_value_survives(self, js, call, roundtrip):
        every = list(range(256))
        blob = js.eval(f'makeBlob("spectre", 0, {every})')
        assert call(f'readBlob({blob!r}, "spectre", 256)')['body'] == every

    @pytest.mark.parametrize('length', [0, 1, 2, 3, 4, 5, 1200, 1501])
    def test_any_length_survives(self, js, call, roundtrip, length):
        """Base64 pads in threes; the lengths either side of a boundary are where it goes wrong."""
        body = [(i * 7) % 256 for i in range(length)]
        blob = js.eval(f'makeBlob("spectre", 1, {body})')
        assert call(f'readBlob({blob!r}, "spectre", {length})')['body'] == body

    def test_the_numeric_types_survive(self, js, call):
        assert call('''(function () {
            const blob = Submission.encode("spectre", 2,
                w => w.u8(200).u16(65535).i16(-32768).i16(32767).f32(0.1));
            const d = Submission.decode(blob, "spectre").reader;
            return [d.u8(), d.u16(), d.i16(), d.i16(), Math.abs(d.f32() - 0.1) < 1e-7];
        })()''') == [200, 65535, -32768, 32767, True]


class TestThePasteSurvivesAWordProcessor:
    """
    The one property the whole design rests on: anything that is not a base64 character is thrown
    away before decoding. Line wrapping, stray spaces and a hyphen inserted where a long run was
    broken are therefore not damage at all.
    """

    @pytest.fixture
    def blob(self, js, roundtrip):
        return js.eval(f'makeBlob("spectre", 4, {BODY})')

    @pytest.mark.parametrize('mangle', [
        lambda b: '\n'.join(b[i:i + 40] for i in range(0, len(b), 40)),   # wrapped
        lambda b: ' '.join(b[i:i + 8] for i in range(0, len(b), 8)),      # grouped
        lambda b: b.replace('', ' ').strip(),                             # spaced out entirely
        lambda b: b[:20] + '-\n' + b[20:],                                # hyphenated at a break
        lambda b: b[:20] + '­' + b[20:],                             # a soft hyphen
        lambda b: '\t' + b + '\r\n',                                      # whatever the editor adds
        lambda b: b[:20] + '—' + b[20:],                             # an em dash from autocorrect
    ], ids=['wrapped', 'grouped', 'spaced', 'hyphenated', 'soft-hyphen', 'padded', 'em-dash'])
    def test_it_still_decodes(self, call, blob, mangle):
        assert call(f'readBlob({mangle(blob)!r}, "spectre", {len(BODY)})')['body'] == BODY


class TestEveryFailureIsNamed:
    """
    "It did not work" is no use to somebody holding a PDF. Each refusal has to say whether to
    re-copy the block, re-export the document, or open a different page.
    """

    @pytest.fixture
    def blob(self, js, roundtrip):
        return js.eval(f'makeBlob("spectre", 4, {BODY})')

    def test_a_changed_character_is_caught(self, js, blob):
        for i in range(0, len(blob) - 4):
            other = 'B' if blob[i] == 'A' else 'A'
            damaged = blob[:i] + other + blob[i + 1:]
            assert js.eval(f'failure({damaged!r}, "spectre", {len(BODY)})') == 'damaged', i

    def test_a_truncated_block_is_caught(self, js, blob):
        assert js.eval(f'failure({blob[:12]!r}, "spectre", {len(BODY)})') == 'damaged'

    def test_a_block_too_short_to_be_anything_is_caught(self, js):
        assert js.eval('failure("AAAA", "spectre", 1)') == 'truncated'

    def test_nothing_at_all_is_caught(self, js):
        assert js.eval('failure("   ...   ", "spectre", 1)') == 'empty'

    def test_another_problems_state_is_refused_by_name(self, js, roundtrip):
        blob = js.eval('makeBlob("heat-transport", 1, [1, 2, 3])')
        assert js.eval(f'failure({blob!r}, "spectre", 3)') == 'wrong-app'
        assert 'heat-transport' in js.eval(
            f'(function () {{ try {{ readBlob({blob!r}, "spectre", 3); }} '
            f'catch (e) {{ return e.message; }} }})()')

    def test_a_newer_format_is_refused(self, js, roundtrip):
        """A future version says so, rather than reading the body against the wrong layout."""
        blob = js.eval(f'''(function () {{
            const bytes = Submission.fromBase64(makeBlob("spectre", 4, {BODY}));
            bytes[0] = 99;
            const body = bytes.subarray(0, bytes.length - 2);
            const crc = Submission.crc16(body);
            const all = new Uint8Array(bytes.length);
            all.set(body); all[body.length] = crc >> 8; all[body.length + 1] = crc & 255;
            return Submission.toBase64(all);
        }})()''')
        assert js.eval(f'failure({blob!r}, "spectre", {len(BODY)})') == 'future'

    def test_an_unregistered_app_cannot_be_encoded(self, js):
        assert js.eval('(function () { try { Submission.encode("nope", 0, w => w.u8(1)); } '
                       'catch (e) { return e.code; } })()') == 'unknown-app'


class TestTheCharacterCountIsOneNumber:
    """
    The panel prints a count when it saves and the error prints one when a paste fails, and a
    participant is meant to compare them. They have to be counted the same way -- `clean` drops
    the `=` padding as well as the whitespace, so stripping whitespace by hand gives a different
    number and turns a good block into a scare.
    """

    def test_clean_ignores_padding_and_whitespace(self, js, call, roundtrip):
        blob = js.eval(f'makeBlob("spectre", 1, {BODY})')
        assert js.eval(f'Submission.clean({blob!r}).length') \
            == js.eval(f'Submission.clean({blob!r}.replace(/=/g, "")).length')

    def test_the_padding_is_not_needed_to_decode(self, js, call, roundtrip):
        blob = js.eval(f'makeBlob("spectre", 1, {BODY})')
        assert call(f'readBlob({blob!r}.replace(/=/g, ""), "spectre", {len(BODY)})')['body'] == BODY


class TestTheRegistryIsAppendOnly:
    """
    An app id is a byte inside blocks that are already in people's documents. These numbers may
    be added to and never reassigned, which is worth a test rather than only a comment.
    """

    def test_the_ids_are_what_they_were(self, call):
        assert call('Submission.APPS') == {'spectre': 1, 'heat-transport': 2, 'charges': 3}
