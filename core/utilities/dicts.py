"""
Dict utilities. Made by Claude.
"""


def strict_merge(*dicts: dict) -> dict:
    """
    Merge multiple dicts, raising ValueError if two of them assign different
    values to the same key. Identical assignments are silently coalesced;
    non-overlapping keys merge cleanly.

    Comparison uses ``==``, so nested structures are compared by value.

    >>> strict_merge({'a': 1}, {'b': 2})
    {'a': 1, 'b': 2}
    >>> strict_merge({'a': 1}, {'a': 1})
    {'a': 1}
    >>> strict_merge({'a': 1}, {'a': 2})
    Traceback (most recent call last):
        ...
    ValueError: Conflicting values for key 'a': 1 vs 2
    """
    result: dict = {}
    for source in dicts:
        for key, value in source.items():
            if key in result and result[key] != value:
                raise ValueError(
                    f"Conflicting values for key {key!r}: "
                    f"{result[key]!r} vs {value!r}"
                )
            result[key] = value
    return result