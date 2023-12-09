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
    default_suffix_map = {
        '.jtt': '.tex',
        '.jyt': '.yaml',
    }

    def __init__(self, *, suffix_map: dict[str, str] = None):
        """
        suffix_map: translates template suffixes to rendered template suffixes
                    and also provides a default for dgs
        """
        self.parser = argparse.ArgumentParser(description="Build a dgs LaTeX template set from repository")
        self.add_core_arguments()
        self.add_arguments()
        self.args = self.parser.parse_args()

        log.setLevel(logging.DEBUG if self.args.debug else logging.INFO)
        self.launch_directory = Path(self.args.launch)
        self.template_root = Path(self.args.template_root)
        self.output_directory = Path(self.args.output) if self.args.output else None
        self.context = self._root_context_class(self.launch_directory, *self.ident())
        self.suffix_map = self.default_suffix_map if suffix_map is None else suffix_map

    def add_core_arguments(self) -> None:
        """ Create the default ArgumentParser """
        self.parser.add_argument('launch', action=argparsedirs.ReadableDir)
        self.parser.add_argument('template_root', action=argparsedirs.ReadableDir)
        self.parser.add_argument('-o', '--output', action=argparsedirs.WriteableDir)
        self.parser.add_argument('-d', '--debug', action='store_true')
        self.parser.add_argument('-t', '--tree', action='store_true')

    @abstractmethod
    def add_arguments(self) -> None:
        """ Add extra arguments for specific builders """

    def full_name(self) -> str:
        """ Full name of the builder for log reporting """
        return '/'.join(map(str, self.ident()))

    def full_path(self):
        """ Full path of the builder """
        return Path(self.launch_directory, *self.path())

    @abstractmethod
    def ident(self):
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
        print(self.context.schema)

    def print_build_info(self) -> None:
        """ Prints build info for progress reports """
        log.info(f"{c.act('Invoking')} {c.name(self.module)} {c.act('template builder on')} "
                 f"{c.meta(self._target)} {c.name(self.full_name())} at {c.path(self.full_path())}")

    def print_dir_info(self) -> None:
        """ Prints directory tree info (probably only useful for debugging) """
        log.debug(f"{c.act('Directory structure:')}")
        crawler.Crawler(Path(self.launch_directory, *self.path())).print_path()

    def output_path(self, template_name, *, override_name=None) -> Path:
        """
        Default output naming scheme:  can be overridden """
        path = Path(template_name)
        if path.suffix in self.suffix_map:
            if override_name is None:
                return path.with_suffix(self.suffix_map.get(path.suffix))
            else:
                return Path(override_name).with_suffix(self.suffix_map.get(path.suffix))
        else:
            raise ValueError(f"Unknown template suffix {path.suffix}, {self.__class__.__name__} "
                             f"only supports {', '.join(self.suffix_map.keys())}")

    def build_templates(self, *, new_name: str = None) -> None:
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
                                 new_name=self.output_path(template, override_name=new_name))

        log.debug(f"{c.ok('Template builder on')} {c.name(self._target)} "
                  f"{c.path(self.full_name())} {c.ok('successful')}")

    def build_contexts(self) -> None:
        for context in self.contexts:
            assert isinstance(context, BuildableContext), \
                c.err(f"Builder's context class {context} is {self.context.__class__.__name__}, "
                      f"which is not a buildable context!")

            for template in self.templates:
                jinja.print_template(self.template_root, template, context.data,
                                     outdir=self.output_directory,
                                     new_name=f"{context.name}.tex")
