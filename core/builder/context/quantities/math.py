from typing import Optional

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

    def __format__(self, spec: Optional[str] = None):
        match spec:
            case None:
                return self.__str__()
            case 'disp':
                content = re.sub(r'^(?!\Z)', '    ', self.content, flags=re.MULTILINE)
                return f"""$$\n{content}\n$$ {{#eq:{self.id}}}"""
            case 'align':
                content = re.sub(r'^(?!\Z)', '    ', self.content, flags=re.MULTILINE)
                return f"""$${{\n{content}\n}}$$ {{#eq:{self.id}}}"""
