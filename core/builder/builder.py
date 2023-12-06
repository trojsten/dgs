import pprint
import argparse
import typing

import argparsedirs
import logging
import os
import subprocess

from pathlib import Path
from abc import abstractmethod, ABCMeta

from core.utilities import colour as c, crawler
from core.builder import jinja
from core.builder.context import BuildableContext


log = logging.getLogger('dgs')


def empty_if_none(string):
    return '' if string is None else string


def check_output(command, *, cwd) -> str:
    return subprocess.check_output(command, cwd=cwd if cwd is not None else os.getcwd()).decode().rstrip("\n")


def get_last_commit_hash(cwd=None) -> str:
    return check_output(["git", "rev-parse", "--short", "--verify", "master"], cwd=cwd)


def get_branch(cwd=None) -> str:
    return check_output(["git", "rev-parse", "--symbolic-full-name", "--abbrev-ref", "HEAD"], cwd=cwd)


class BaseBuilder(metaclass=ABCMeta):
    module = None
    templates = []
    _target: str = None
    _root_context_class: typing.ClassVar = None

    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Prepare a DGS input dataset from repository")
        self.add_arguments()
        self.args = self.parser.parse_args()

        self.launch_directory = Path(self.args.launch)
        self.template_root = Path(self.args.template_root)
        self.output_directory = Path(self.args.output) if self.args.output else None
        log.setLevel(logging.DEBUG if self.args.debug else logging.INFO)
        self.context = self._root_context_class(self.launch_directory, *self.id())

    def add_arguments(self):
        """ Create the default ArgumentParser """
        self.parser.add_argument('launch', action=argparsedirs.ReadableDir)
        self.parser.add_argument('template_root', action=argparsedirs.ReadableDir)
        self.parser.add_argument('-o', '--output', action=argparsedirs.WriteableDir)
        self.parser.add_argument('-d', '--debug', action='store_true')
        self.parser.add_argument('-t', '--tree', action='store_true')
        return self.parser

    def full_name(self):
        return '/'.join(map(str, self.id()))

    def full_path(self):
        return Path(self.launch_directory, *self.path())

    @abstractmethod
    def id(self):
        """ Return the id tuple """

    @abstractmethod
    def path(self):
        """ Return the root path for this builder """

    def print_debug_info(self) -> None:
        """ Prints debug info """
        log.debug(c.act("Content templates:"))
        pprint.pprint(self.templates)

        log.debug(c.act("Context:"))
        self.context.print()

        log.debug(c.act("Schema:"))
        pprint.pprint(self.context.schema)

    def print_build_info(self) -> None:
        """ Prints build info """
        log.info(f"{c.act('Invoking')} {c.name(self.module)} {c.act('template builder on')} "
                 f"{c.name(self._target)} {c.path(self.full_path())}")

    def print_dir_info(self) -> None:
        """ Prints directory info """
        log.debug(f"{c.act('Directory structure:')}")
        crawler.Crawler(Path(self.launch_directory, *self.path())).print_path()

    def build_templates(self, *, new_name: str = None, new_suffix: str = None) -> None:
        assert isinstance(self.context, BuildableContext), \
            c.err(f"Builder's context class is {self.context.__class__.__name__}, which is not a buildable context!")
        self.print_build_info()

        if self.args.debug:
            self.print_debug_info()

        if self.args.tree:
            self.print_dir_info()

        for template in self.templates:
            jinja.print_template(self.template_root, template, self.context.data,
                                 outdir=self.output_directory,
                                 new_name=Path(template).with_suffix('.tex') if new_name is None else f"{new_name}.tex")

        log.debug(f"{c.ok('Template builder on')} {c.name(self._target)} "
                  f"{c.path(self.full_name())} {c.ok('successful')}")

    def build_contexts(self) -> None:
        for context in contexts:
            jinja.print_template(self.template_root, template, context.data,
                                 outdir=self.output_directory,
                                 new_name=f"{context.name}.tex")