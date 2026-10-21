#!/usr/bin/env python

import argparse
import contextlib
import logging
import pathlib
import sys
from abc import abstractmethod

from core import i18n
from core.utilities import colour as c

log = logging.getLogger('dgs')


class CLIInterface:
    description: str = "<empty>"

    def __init__(self):
        self.parser = argparse.ArgumentParser(description=self.description)
        self.add_default_arguments()
        self.add_extra_arguments()
        self.args = self.parser.parse_args()

        if self.args.debug:
            log.setLevel(logging.DEBUG)

        # Opened here, before `build_convertor`, because every convertor takes streams rather
        # than paths: `Convertor` reads `infile` line by line and `BuilderStandalone` calls
        # `readlines()` on it. `argparse.FileType` used to do this during parsing and is
        # deprecated; what it bought that a bare `open()` does not is a clean argparse error
        # for a file that will not open, which `open_argument` keeps.
        self.files = contextlib.ExitStack()
        self.infile = self.open_argument('infile', self.args.infile, 'r', sys.stdin)
        self.outfile = self.open_argument('outfile', self.args.outfile, 'w', sys.stdout)

        self.convertor = self.build_convertor(self.args)

    def open_argument(self, name: str, path: pathlib.Path | None, mode: str, standard):
        """
        One path argument as a stream, or the standard stream it falls back to.

        `None` means the argument was omitted -- that is what `nargs='?'` leaves behind now that
        the default is no longer `sys.stdin` itself. The standard streams are returned as they
        are and never entered into the stack: closing them would take the rest of the process
        down with the file.
        """
        if path is None:
            return standard
        try:
            return self.files.enter_context(path.open(mode))
        except OSError as e:
            # the shape `FileType` used, so a missing file still exits 2 with one line rather
            # than a traceback out of the middle of the build
            self.parser.error(f"argument {name}: can't open '{path}': {e.strerror}")

    @property
    def infile_name(self) -> str:
        r"""
        What to call the input in a message.

        **Not `self.args.infile.name`**, which is a different string now: on the file object
        `FileType` produced it was the path as typed, and on a `pathlib.Path` it is the
        basename alone. Reading one for the other turns
        `source/naboj/phys/29/problems/drenched/sk/solution.md` into `solution.md` in every
        error this class prints, with nothing raised to say so.
        """
        return '<stdin>' if self.args.infile is None else str(self.args.infile)

    @abstractmethod
    def build_convertor(self, args, **kwargs):
        pass

    def add_default_arguments(self):
        self.parser.add_argument('locale',   choices=i18n.languages.keys())
        self.parser.add_argument('infile',   nargs='?', type=pathlib.Path)
        self.parser.add_argument('outfile',  nargs='?', type=pathlib.Path)
        self.parser.add_argument('-v', '--verbose', action='store_true')
        self.parser.add_argument('-d', '--debug', action='store_true')

    @staticmethod
    def add_extra_arguments():
        pass

    def run(self) -> None:
        try:
            output = self.convertor.run()
            print(output, file=self.outfile)
            self.success()
        except Exception as e:
            self.fail(e)
        finally:
            # `FileType` never closed anything either, and for a command that exits straight
            # afterwards that is harmless. This one re-raises out of `fail`, so the close is
            # worth making explicit. A caller that does its work in `build_convertor` and never
            # reaches here -- `standalone.py` -- still closes at process exit, as before.
            self.files.close()

    def fail(self, e):
        log.error(f"{c.err('convert: failure on ')}{c.path(self.infile_name)}")
        raise e

    def success(self):
        if self.args.verbose:
            log.info(f"convert: {c.ok('success')} on {c.path(self.infile_name)}")
