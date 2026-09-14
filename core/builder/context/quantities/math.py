import regex as re


class MathObject:
    """
    A representation of a named LaTeX math object.
    """
    def __init__(self,
                 ident: str,
                 content: str):
        self.id = ident
        self.content = re.sub(r'\n\Z', '', content)

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

    @staticmethod
    def _shield_brackets(content: str) -> str:
        r"""
        Put `{}` in front of a row that starts with `[`.

        LaTeX's `\\` takes an optional length, so a row beginning with a bracket -- a concentration
        `[A]`, an interval, a unit in square brackets -- is read as `\\[A]` and the compile dies on
        `Missing number, treated as zero`. amsmath's `aligned` does not scan for that argument and
        so tolerates it, which is why the problem only appears on the way *in* to an array:
        `01/rovnováha` had written `[A] … \\ [B] …` happily for years.
        """
        rows, out = re.split(r'(?<=\\\\)\n', content), []
        for row in rows:
            stripped = row.lstrip()
            if stripped.startswith('['):
                pad = row[:len(row) - len(stripped)]
                row = f'{pad}{{}}{stripped}'
            out.append(row)
        return '\n'.join(out)

    @classmethod
    def _display_columns(cls, columns: str) -> str:
        r"""
        Put every column of an array in display style.

        `array` sets its cells in **text** style, so a `\frac` inside one comes out at script
        size -- next to an `aligned` block on the same page the difference is glaring. `array`'s
        `>{…}` prefix fixes it per column, which is why `core/latex/wrt.tex` requires the `array`
        package. Authors never write this; they write `|arr('rclcl')` and get it.
        """
        return ''.join(f'>{{\\displaystyle}}{c}' if c in cls._COLUMN_TYPES else c
                       for c in columns)

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
            # Eight spaces, not four: `\begin{array}` sits where `disp`'s content would, and the
            # rows sit inside it. The punctuation lands on the end of the last row -- inside the
            # final cell, where it belongs. Put after `\end{array}` it would float at the array's
            # vertical centre, beside the middle row.
            body = self._shield_brackets(self.content)
            content = re.sub(r'^(?!\Z)', '        ', body, flags=re.MULTILINE)
            return (f"$$\n    \\begin{{array}}{{{self._display_columns(columns)}}}\n"
                    f"{content}{interpunction}\n"
                    f"    \\end{{array}}\n$$ {{#eq:{self.id}}}")

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

        match spec:
            case '':
                return self.content
            case 'inl':
                return f"${self.content}$"
            case 'disp':
                content = re.sub(r'^(?!\Z)', '    ', self.content, flags=re.MULTILINE)
                return f"$$\n{content}{interpunction}\n$$ {{#eq:{self.id}}}"
            case 'align':
                content = re.sub(r'^(?!\Z)', '    ', self.content, flags=re.MULTILINE)
                return f"$${{\n{content}{interpunction}\n}}$$ {{#eq:{self.id}}}"
            case _:
                raise NotImplementedError(f"Unknown format spec {spec!r} for MathObject")