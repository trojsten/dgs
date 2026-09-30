"""
The standalone one-problem preview takes its volume as a directory name, not a number: a real
volume is `05`, and the problems that belong to no volume yet live in `pool`.
"""
from modules.naboj.builder.standalone import UNNUMBERED, problem_number


def test_a_volume_numbers_the_problem_from_its_list(tmp_path):
    (tmp_path / 'phys' / '05').mkdir(parents=True)
    (tmp_path / 'phys' / '05' / 'meta.yaml').write_text('problems: [late-train, hanging-rope]\n')
    assert problem_number(tmp_path, 'phys', '05', 'hanging-rope') == '2'


def test_the_pool_is_a_volume_without_a_running_order(tmp_path):
    # No `pool/meta.yaml`, so nothing to number against. That used to be unreachable: parsing
    # the volume as an int refused `pool` before anything was read.
    (tmp_path / 'phys' / 'pool' / 'problems' / 'troll-69').mkdir(parents=True)
    assert problem_number(tmp_path, 'phys', 'pool', 'troll-69') == UNNUMBERED
