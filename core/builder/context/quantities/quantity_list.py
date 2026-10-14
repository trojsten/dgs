from .aggregate import QuantitySequence


class QuantityList(QuantitySequence):
    r"""
    A list of commensurate quantities: `\qtylist{1;2;3}{\metre}`, printed `1 m, 2 m, 3 m`.

    What separates them on the page is `list-separator` in `core/latex/siunitx.tex`, not the `;`
    here, which is only how siunitx wants the input.
    """
    _KIND = 'list'
