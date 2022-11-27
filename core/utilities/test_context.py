import pytest
from .context import Context, split_mod, split_div, split_callback, is_prime


class TestContext():
    def test_splitmod(self):
        assert split_mod(list(range(0, 12)), 3) == [[0, 3, 6, 9], [1, 4, 7, 10], [2, 5, 8, 11]]

    def test_splitmod_2(self):
        assert split_mod(list(range(0, 17)), 5) == [[0, 5, 10, 15], [1, 6, 11, 16], [2, 7, 12], [3, 8, 13], [4, 9, 14]]

    def test_splitdiv(self):
        assert split_div(list(range(0, 12)), 3) == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]

    def test_splitdiv_2(self):
        assert split_div(list(range(0, 17)), 5) == [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9], [10, 11, 12, 13, 14], [15, 16]]

    def test_split_callback(self):
        assert split_callback(list(range(0, 12)), is_prime, 2) == [[0, 1, 4, 6, 8, 9, 10], [2, 3, 5, 7, 11]]

    def test_split_callback_bad_count(self):
        with pytest.raises(IndexError):
            assert split_callback(list(range(0, 12)), is_prime, 1)


