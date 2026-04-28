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
        return f"${self.content}$"

    def __repr__(self):
        return repr(self.__str__())

    _INTERPUNCTION = '.,;?!'

    def __format__(self, spec: str = ''):
        interpunction = ''
        if len(spec) > 0 and spec[-1] in self._INTERPUNCTION:
            interpunction = spec[-1]
            spec = spec[:-1]

        match spec:
            case '':
                return f"${self.content}{interpunction}$"
            case 'disp':
                content = re.sub(r'^(?!\Z)', '    ', self.content, flags=re.MULTILINE)
                return f"$$\n{content}{interpunction}\n$$ {{#eq:{self.id}}}"
            case 'align':
                content = re.sub(r'^(?!\Z)', '    ', self.content, flags=re.MULTILINE)
                return f"$${{\n{content}{interpunction}\n}}$$ {{#eq:{self.id}}}"
            case _:
                raise NotImplementedError(f"Unknown format spec {spec!r} for MathObject")
