import regex as re

from . import backend as _backend


class MathObject:
    """
    A named equation, written in whatever markup this render is for.

    **The markup is not the equation.** Which delimiters a display takes, how its rows align and
    what a label looks like are `markup.py`'s business; what belongs here is everything that is
    the same in every markup -- which format specs exist, what a trailing punctuation mark may
    attach to, and whether this display is labelled at all.
    """
    def __init__(self,
                 ident: str,
                 content: str,
                 labelled: bool = True):
        self.id = ident
        self.content = re.sub(r'\n\Z', '', content)
        #: Whether a display carries its `{#eq:…}` label, and so an equation number.
        #:
        #: **A problem statement never numbers its equations and never labels them**, because a
        #: number is a cross-reference to something the contestant cannot see -- the solution is
        #: not in their hands during the competition -- and a label no one may point at is just a
        #: number in the margin. The renderer sets this from the file it is rendering rather than
        #: leaving it to a filter, so an author cannot pick the wrong one: see
        #: `JinjaCLIInterface.build_context`.
        #:
        #: It is what lets one `eq:` entry serve both halves of a problem. `26/earthquakes` states
        #: the Gutenberg-Richter law and then opens its solution with it; written as
        #: `(§ eq.grl|disp(\',\') §)` in both, the statement gets no label and the solution gets
        #: one, so there is a single copy of the equation and still exactly one `{#eq:}` to
        #: reference. Labelling both would be a duplicate label.
        self.labelled = labelled

    @property
    def _label(self) -> str:
        return _backend.markup().equation_label(self.id) if self.labelled else ""

    def __str__(self):
        """
        Raw, undecorated content -- `(§ eq.foo §)` includes the fragment and nothing else.

        Math delimiters are a rendering choice and belong to the filter that makes one: `|inl`
        for inline, `|disp` for display, `|align` for an aligned block. A bare reference is for
        building a larger expression out of a named piece, where any wrapping the fragment
        brought with it would have to be undone.
        """
        return self.content

    def __repr__(self):
        return repr(self.__str__())

    _INTERPUNCTION = '.,;?!'
    _BASE_SPECS = {'', 'inl', 'disp', 'align'}
    _SPECS_ACCEPTING_PUNCTUATION = {'disp', 'align'}

    #: `arr:<columns>` is the one spec that carries an argument, because an array has no sensible
    #: default column layout the way `aligned` does.
    _ARRAY_PREFIX = 'arr:'
    _COLUMN_TYPES = frozenset('lcr')

    def __format__(self, spec: str = ''):
        interpunction = ''
        if len(spec) > 0 and spec[-1] in self._INTERPUNCTION:
            interpunction = spec[-1]
            spec = spec[:-1]

        if spec.startswith(self._ARRAY_PREFIX):
            columns = spec[len(self._ARRAY_PREFIX):]
            if not columns:
                raise ValueError(
                    "`arr` needs a column spec and has no default: write `|arr('rclcl')`"
                )
            unknown = set(columns) - self._COLUMN_TYPES - set('|')
            if unknown:
                raise ValueError(
                    f"Unknown array column type(s) {''.join(sorted(unknown))!r}; "
                    f"expected only {''.join(sorted(self._COLUMN_TYPES))} and `|`"
                )
            return _backend.markup().array(self.content, columns=columns,
                                           label=self._label, punctuation=interpunction)

        # Distinguish "unknown base spec" from "valid base spec with invalid
        # trailing character," because the latter is the much more common
        # author mistake.
        if spec not in self._BASE_SPECS:
            if len(spec) > 1 and spec[:-1] in self._BASE_SPECS:
                raise ValueError(
                    f"Invalid trailing character {spec[-1]!r} in MathObject "
                    f"format spec; expected one of {''.join(self._INTERPUNCTION)} "
                    f"or no trailing character"
                )
            raise NotImplementedError(
                f"Unknown format spec {spec!r} for MathObject; "
                f"expected one of {sorted(self._BASE_SPECS - {''})} or empty"
            )

        # Neither a raw include nor inline math needs in-math punctuation — authors can simply
        # type the punctuation outside, after the closing $.
        if interpunction and spec not in self._SPECS_ACCEPTING_PUNCTUATION:
            raise ValueError(
                f"{spec or 'A raw include'} does not accept trailing punctuation; "
                f"write the punctuation outside the math instead: "
                f"`(§ eq.foo|inl §){interpunction}`"
            )

        markup = _backend.markup()
        match spec:
            case '':
                return self.content
            case 'inl':
                return markup.inline(self.content)
            case 'disp':
                return markup.display(self.content, label=self._label,
                                      punctuation=interpunction)
            case 'align':
                return markup.aligned(self.content, label=self._label,
                                      punctuation=interpunction)
            case _:
                raise NotImplementedError(f"Unknown format spec {spec!r} for MathObject")
