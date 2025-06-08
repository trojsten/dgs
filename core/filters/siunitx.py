from .numbers import exp


def num(x: float, precision: int):
    """ Format as a `siunitx` \num{} input"""
    return rf'\num{{{exp(x, precision)}}}'
