r"""
Finding the drawings, which arrive as a crowd of paths and no markup at all.
"""

from tools.ancient.pdf.assemble import _figures, _lettering
from tools.ancient.pdf.draft import pictures
from tools.ancient.pdf.glyphs import Box


def box(x0, y0, x1, y1, kind='stroke_path'):
    return Box(kind, x0, y0, x1, y1)


class TestFigures:
    def test_a_crowd_of_strokes_is_one_drawing(self):
        parts = [box(100, -200, 140, -160), box(138, -205, 180, -158),
                 box(120, -210, 160, -170)]
        assert len(_figures(parts)) == 1

    def test_two_crowds_far_apart_are_two_drawings(self):
        near = [box(100, -200, 140, -160), box(138, -205, 180, -158)]
        far = [box(100, -600, 140, -560), box(138, -605, 180, -558)]
        assert len(_figures(near + far)) == 2

    def test_they_come_back_top_first(self):
        near = [box(100, -200, 150, -150)]
        far = [box(100, -600, 150, -550)]
        assert _figures(far + near) == sorted(_figures(far + near), reverse=True)

    def test_a_rule_is_not_a_drawing(self):
        # The header rule at the top of every page, which is wide and hair-thin. Left in, it
        # merges with the first line of prose and reports a figure on all 24 pages.
        assert _figures([box(60, -100, 540, -99.5)]) == []

    def test_one_small_mark_is_not_a_drawing(self):
        assert _figures([box(100, -200, 110, -190)]) == []

    def test_outlined_lettering_is_not_a_drawing(self):
        # `08`'s chapter heading is set as outlines, so `Kapitola 1` arrives as nine filled
        # paths that cluster into a tidy 140x25 rectangle and look exactly like a diagram.
        heading = [box(66 + 16 * i, -185.5, 78 + 16 * i, -166, 'fill_path') for i in range(9)]
        assert _lettering(heading)
        assert _figures(heading) == []

    def test_a_baseline_is_matched_within_a_tolerance(self):
        # The quiet case that caught this out: those bottoms are -185.5 and -185.6, which
        # `round` splits four and four across the -185/-186 boundary.
        letters = [box(10 * i, -185.5 if i % 2 else -185.6, 10 * i + 8, -170, 'fill_path')
                   for i in range(8)]
        assert _lettering(letters)

    def test_a_diagram_whose_parts_wander_is_not_lettering(self):
        scattered = [box(100, -200 - 9 * i, 140, -160 - 9 * i) for i in range(5)]
        assert not _lettering(scattered)


class TestPlaceholders:
    def test_every_marker_becomes_a_placeholder(self):
        from tools.ancient.pdf.assemble import FIGURE
        out = pictures(f'Text.\n{FIGURE}\nMore.\n{FIGURE}\n')
        assert out.count('![](){height=40mm}') == 2

    def test_the_path_is_empty(self):
        # `convertor.py` carries a rule for exactly this; its other picture rules match on the
        # extension, so before that rule an empty path stayed a bare `\includegraphics{}` and
        # stopped xelatex with ``File `' not found``.
        from tools.ancient.pdf.assemble import FIGURE
        assert pictures(FIGURE).strip() == '![](){height=40mm}'

    def test_prose_that_promises_a_figure_gets_one_anyway(self):
        out = pictures('Na obrázku je zobrazený dej.\n')
        assert out.count('![](){height=40mm}') == 1

    def test_prose_that_already_has_one_does_not_get_a_second(self):
        from tools.ancient.pdf.assemble import FIGURE
        out = pictures(f'Na obrázku je dej.\n{FIGURE}\n')
        assert out.count('height=40mm') == 1

    def test_prose_that_mentions_nothing_gets_nothing(self):
        assert 'height=40mm' not in pictures('Teleso padá z výšky.\n')
