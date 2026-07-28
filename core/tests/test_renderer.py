from core.builder.renderer import JinjaConvertor


def make_convertor(preamble):
    convertor = JinjaConvertor.__new__(JinjaConvertor)
    convertor.preamble = preamble
    return convertor


class TestPrepareTemplate:
    def test_no_preamble(self):
        assert make_convertor(None).prepare_template("body") == "body"

    def test_empty_preamble(self):
        assert make_convertor("").prepare_template("body") == "body"

    def test_whitespace_only_preamble(self):
        assert make_convertor("   \n\n").prepare_template("body") == "body"

    def test_single_trailing_newline(self):
        assert make_convertor("@J set x = 1\n").prepare_template("body") == "@J set x = 1\nbody"

    def test_multiple_trailing_newlines_collapse_to_one(self):
        assert make_convertor("@J set x = 1\n\n\n").prepare_template("body") == "@J set x = 1\nbody"

    def test_no_trailing_newline_still_gets_one(self):
        assert make_convertor("@J set x = 1").prepare_template("body") == "@J set x = 1\nbody"
