import pprint
import argparse
from pathlib import Path

from core.utilities import colour as c, argparser, jinja


def empty_if_none(string):
    return '' if string is None else string


class BaseBuilder():
    def __init__(self):
        self.create_argument_parser()
        self.args = self.parser.parse_args()

        self.launch_directory = Path(self.args.launch)
        self.template_root = Path(self.args.template_root)
        self.output_directory = Path(self.args.output) if self.args.output else None
        self.create_context()

    def create_argument_parser(self):
        self.parser = argparse.ArgumentParser(description="Prepare a DGS input dataset from repository")
        self.parser.add_argument('launch', action=argparser.readable_dir)
        self.parser.add_argument('template_root', action=argparser.readable_dir)
        self.parser.add_argument('-o', '--output', action=argparser.writeable_dir)
        self.parser.add_argument('-d', '--debug', action='store_true')
        return self.parser

    def create_context(self):
        self.context = self.root_context_class(self.launch_directory, *self.id())

    def full_name(self):
        return '/'.join(map(str, self.id()))

    def id(self):
        raise NotImplementedError("Child classes of BaseBuilder must implement `id`")

    def path(self):
        raise NotImplementedError("Child classes of BaseBuilder must implement `path`")

    def print_debug_info(self):
        """ Prints debug info (only when args.debug is True) """
        if self.args.debug:
            print("Launched {target} builder in {dir}".format(
                target=c.name(self.target),
                dir=c.path(self.args.launch),
            ))
            print(c.act("Content templates:"))
            pprint.pprint(self.templates)

            print(c.act("Context:"))
            self.context.print()

    def print_build_info(self):
        """ Prints build info (always) """
        print(f"{c.act('Invoking')} {c.name(self.module)} {c.act('template builder on')} {c.name(self.target)} {c.path(self.full_name())}")

    def build(self):
        self.print_debug_info()
        self.print_build_info()

        for template in self.templates:
            jinja.print_template(self.template_root, template, self.context.data, self.output_directory)

        print(f"{c.ok('Template builder on')} {c.name(self.target)} {c.path(self.full_name())} {c.ok('successful')}")
