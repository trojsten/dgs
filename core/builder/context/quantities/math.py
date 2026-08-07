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

    def __format__(self, spec: str = ''):
        interpunction = ''
        if len(spec) > 0 and spec[-1] in self._INTERPUNCTION:
            interpunction = spec[-1]
            spec = spec[:-1]

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