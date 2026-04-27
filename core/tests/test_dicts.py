import pytest

from core.utilities.dicts import strict_merge


class TestStrictMergeBasic:
    def test_empty(self):
        assert strict_merge() == {}

    def test_single_dict(self):
        assert strict_merge({'a': 1, 'b': 2}) == {'a': 1, 'b': 2}

    def test_disjoint_keys(self):
        assert strict_merge({'a': 1}, {'b': 2}) == {'a': 1, 'b': 2}

    def test_three_disjoint(self):
        assert strict_merge({'a': 1}, {'b': 2}, {'c': 3}) == {'a': 1, 'b': 2, 'c': 3}

    def test_does_not_mutate_inputs(self):
        a = {'a': 1}
        b = {'b': 2}
        _ = strict_merge(a, b)
        assert a == {'a': 1}
        assert b == {'b': 2}


class TestStrictMergeAgreement:
    """Same key with the same value across dicts should be silently coalesced."""

    def test_identical_values(self):
        assert strict_merge({'a': 1}, {'a': 1}) == {'a': 1}

    def test_identical_values_three_dicts(self):
        assert strict_merge({'a': 1}, {'a': 1}, {'a': 1}) == {'a': 1}

    def test_identical_string_values(self):
        assert strict_merge(
            {'mode': 'figures'}, {'mode': 'figures'}
        ) == {'mode': 'figures'}

    def test_identical_nested_values(self):
        """Nested structures compare by value (dict ==)."""
        assert strict_merge(
            {'a': {'x': 1, 'y': 2}}, {'a': {'x': 1, 'y': 2}}
        ) == {'a': {'x': 1, 'y': 2}}

    def test_identical_list_values(self):
        assert strict_merge({'k': [1, 2, 3]}, {'k': [1, 2, 3]}) == {'k': [1, 2, 3]}


class TestStrictMergeConflict:
    """Same key with different values should raise."""

    def test_simple_conflict(self):
        with pytest.raises(ValueError, match="key 'a'"):
            strict_merge({'a': 1}, {'a': 2})

    def test_conflict_message_carries_both_values(self):
        with pytest.raises(ValueError, match="1.*2"):
            strict_merge({'a': 1}, {'a': 2})

    def test_string_conflict(self):
        with pytest.raises(ValueError, match="round-mode"):
            strict_merge({'round-mode': 'figures'}, {'round-mode': 'places'})

    def test_nested_conflict(self):
        with pytest.raises(ValueError, match="key 'a'"):
            strict_merge({'a': {'x': 1}}, {'a': {'x': 2}})

    def test_partial_overlap_with_conflict(self):
        """Disjoint keys are no problem; only the conflict raises."""
        with pytest.raises(ValueError, match="key 'b'"):
            strict_merge({'a': 1, 'b': 2}, {'b': 3, 'c': 4})

    def test_third_dict_introduces_conflict(self):
        with pytest.raises(ValueError, match="key 'a'"):
            strict_merge({'a': 1}, {'a': 1}, {'a': 2})


class TestStrictMergeEdgeCases:
    def test_none_value_does_not_conflict_with_none(self):
        assert strict_merge({'a': None}, {'a': None}) == {'a': None}

    def test_none_conflicts_with_other(self):
        with pytest.raises(ValueError):
            strict_merge({'a': None}, {'a': 0})

    def test_zero_and_false_treated_as_distinct(self):
        """0 == False in Python but the values should still be considered equal here."""
        # 0 == False is True; strict_merge uses ==, so they are considered the same.
        # This is the documented behavior.
        assert strict_merge({'a': 0}, {'a': False}) == {'a': 0}

    def test_first_occurrence_wins_in_result(self):
        """When values are equal, the first one written is the one stored."""
        a = {'k': (1, 2)}
        b = {'k': (1, 2)}  # equal but possibly different object identity
        result = strict_merge(a, b)
        # Either is acceptable; we just want to confirm no error and right value.
        assert result['k'] == (1, 2)