r"""
What the editor refuses to write through.

`tools/editor/app.py` has no test that exercises a route -- that gap is its own piece of work --
but `write_through` is a pure function over a path, and it is the one guard standing between a
save and two different accidents. Both halves are pinned here, the quiet one included, because a
guard that refused an ordinary file would make the editor useless in a way nobody would attribute
to it.
"""
import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'tools' / 'editor'))

import app                                                            # noqa: E402


class TestWritingThroughASymlink:
    def test_a_mirrored_translation_is_refused(self, tmp_path):
        """
        The case that will actually happen. 84 files under `source/` are symlinks, deliberately:
        a translation nobody has written yet mirrors its master rather than keeping a stale copy.
        `Path.write_text` follows, so opening the Polish tab and saving rewrote the English
        source -- silently, and under a filename that says Polish.
        """
        master = tmp_path / 'en-solution.md'
        master.write_text('the English text\n')
        mirror = tmp_path / 'pl-solution.md'
        mirror.symlink_to(master)

        with pytest.raises(app.BadRequest) as raised:
            app.write_through(mirror, 'text somebody typed into the Polish tab\n')

        assert 'symlink' in raised.value.message
        assert master.read_text() == 'the English text\n', 'the master was written through'

    def test_a_meta_pointing_out_of_the_tree_is_refused(self, tmp_path):
        """
        The same guard, doing the other job. `source/` is cloned from repositories several
        people push to, so a `meta.yaml` that arrives as a link to something in `$HOME` is
        content, not configuration.
        """
        target = tmp_path / 'authorized_keys'
        target.write_text('# nothing of ours\n')
        meta = tmp_path / 'meta.yaml'
        meta.symlink_to(target)

        with pytest.raises(app.BadRequest):
            app.write_through(meta, 'ssh-ed25519 AAAA...\n')
        assert target.read_text() == '# nothing of ours\n'

    def test_an_ordinary_file_is_written(self, tmp_path):
        """The quiet case, and the one that matters: this is what saving normally is."""
        path = tmp_path / 'solution.md'
        path.write_text('before\n')
        app.write_through(path, 'after\n')
        assert path.read_text() == 'after\n'

    def test_a_new_file_is_written(self, tmp_path):
        """
        Also quiet. `words.yaml` is created on demand -- a problem with no words yet is exactly
        the one somebody is adding words to -- so the guard must not require the file to exist.
        """
        path = tmp_path / 'words.yaml'
        app.write_through(path, 'twin: s\n')
        assert path.read_text() == 'twin: s\n'

    def test_the_message_names_what_the_link_points_at(self, tmp_path):
        """Whoever hits this needs to be told where to go and edit instead."""
        master = tmp_path / 'sk-solution.md'
        master.write_text('x\n')
        mirror = tmp_path / 'cs-solution.md'
        mirror.symlink_to(master)

        with pytest.raises(app.BadRequest) as raised:
            app.write_through(mirror, 'y\n')
        assert os.fspath(master) in raised.value.message
