import pprint
import argparse
import argparsedirs
import schema

from pathlib import Path
from abc import abstractmethod, ABCMeta

from core.utils import colour as c, crawler
from core.builder import jinja
from core.builder.context import BuildableContext


def empty_if_none(string):
    return '' if string is None else string


class BaseBuilder(metaclass=ABCMeta):
    module = None

    def __init__(self):
        self.create_argument_parser()
        self.args = self.parser.parse_args()

        self.launch_directory = Path(self.args.launch)
        self.template_root = Path(self.args.template_root)
        self.output_directory = Path(self.args.output) if self.args.output else None
        self.create_context()

    def create_argument_parser(self):
        """ Create the default ArgumentParser """
        self.parser = argparse.ArgumentParser(description="Prepare a DGS input dataset from repository")
        self.parser.add_argument('launch', action=argparsedirs.ReadableDir)
        self.parser.add_argument('template_root', action=argparsedirs.ReadableDir)
        self.parser.add_argument('-o', '--output', action=argparsedirs.WriteableDir)
        self.parser.add_argument('-d', '--debug', action='store_true')
        self.parser.add_argument('-t', '--tree', action='store_true')
        return self.parser

    def create_context(self):
        self.context = self.root_context_class(self.launch_directory, *self.id())

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
        print(c.act("Content templates:"))
        pprint.pprint(self.templates)

        print(c.act("Context:"))
        self.context.print()

    def print_build_info(self) -> None:
        """ Prints build info """
        print(f"{c.act('Invoking')} {c.name(self.module)} {c.act('template builder on')} {c.name(self.target)} {c.path(self.full_path())}")

    def print_dir_info(self):
        """ Prints directory info """
        print(f"{c.act('Directory structure:')}")
        crawler.Crawler(Path(self.launch_directory, *self.path())).print_path()

    def build(self):
        assert isinstance(self.context, BuildableContext), \
            c.err(f"Builder's context class is {self.context.__class__.__name__}, which is not a buildable context!")
        self.print_build_info()

        if self.args.debug:
            self.print_debug_info()

        if self.args.tree:
            self.print_dir_info()

        for template in self.templates:
            jinja.print_template(self.template_root, template, self.context.data, self.output_directory)

        if self.args.debug:
            print(f"{c.ok('Template builder on')} {c.name(self.target)} {c.path(self.full_name())} {c.ok('successful')}")
