from .numbers import sci


def num(x: float, precision: int):
    """ Format as a `siunitx` \num{} input"""
    return rf'\num{{{sci(x, precision)}}}'
