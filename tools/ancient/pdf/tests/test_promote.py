r"""
Rewriting a volume's `problems:` list without losing what is written around it.

The list is the running order, so promoting a redecoded draft has to replace it -- and the
notes in it are provenance that nothing else records.
"""

from tools.ancient.pdf.promote import _splice_order

META = """\
id: '05'
date: 1900-12-31
problems:
  - late-train
  # %# TODO(duplicate): the booklet prints this problem twice, as 10 and as 22.
  - reversing-tram-again
  - three-balls
constants: []
"""


class TestSpliceOrder:
    def test_the_order_is_replaced(self):
        out = _splice_order(META, ['three-balls', 'late-train'])
        assert '  - three-balls\n  - late-train\n' in out

    def test_everything_around_it_is_left_alone(self):
        out = _splice_order(META, ['late-train'])
        assert out.startswith("id: '05'\ndate: 1900-12-31\n")
        assert out.endswith('constants: []\n')

    def test_a_note_in_the_list_travels_with_its_entry(self):
        # The regression. The block regex used to stop at the first line that was not an
        # entry, so the sub replaced the head of the list and left the tail below the comment
        # exactly where it was: volume 05 came out with 79 problems instead of 50, running 29
        # of them twice, and nothing said so.
        out = _splice_order(META, ['three-balls', 'reversing-tram-again', 'late-train'])
        lines = [ln for ln in out.split('\n') if ln.startswith('  ') or ln.startswith('  #')]
        assert out.count('- reversing-tram-again') == 1
        assert out.count('- late-train') == 1
        note = out.split('\n')[out.split('\n').index('  - reversing-tram-again') - 1]
        assert 'TODO(duplicate)' in note

    def test_a_list_with_no_notes_round_trips(self):
        plain = 'id: x\nproblems:\n  - a\n  - b\nend: y\n'
        assert _splice_order(plain, ['a', 'b']) == plain

    def test_an_empty_list_is_filled(self):
        assert '  - a\n' in _splice_order('problems: []\n', ['a'])
