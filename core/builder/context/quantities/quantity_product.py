from .aggregate import QuantitySequence


class QuantityProduct(QuantitySequence):
    r"""
    A product of commensurate quantities -- the dimensions of a box, say:
    `\qtyproduct{3 x 4 x 5}{\centi\metre}`, printed `3 cm × 4 cm × 5 cm`.

    The ` x ` is siunitx's input syntax; the `×` on the page comes from its own settings.
    """
    _KIND = 'product'
    _SEPARATOR = ' x '
