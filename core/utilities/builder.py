import yaml
import os
import pprint
import argparse

from core.utilities import dicts, colour as c, argparser, jinja


class BaseBuilder():
    def __init__(self):
        self.create_argument_parser()
        self.parse_arguments()

        self.launch_directory = os.path.realpath(self.args.launch)
        self.template_root = os.path.realpath(self.args.template_root)
        self.output_directory = os.path.realpath(self.args.output) if self.args.output else None
        self.create_context()

    def print_debug_info(self):
        if self.args.debug:
            print("Launched {target} builder in {dir}".format(
                target=c.name(self.target),
                dir=c.path(self.args.launch),
            ))
            print(c.act("Content templates:"))
            pprint.pprint(self.templates)

            print(c.act("Context:"))
            self.context.print()

    def create_argument_parser(self):
        self.parser = argparse.ArgumentParser(description="Prepare a DGS input dataset from repository")
        self.parser.add_argument('launch', action=argparser.readable_dir)
        self.parser.add_argument('template_root', action=argparser.readable_dir)
        self.parser.add_argument('-o', '--output', action=argparser.writeable_dir)
        self.parser.add_argument('-d', '--debug', action='store_true')
        return self.parser

    def parse_arguments(self):
        self.args = self.parser.parse_args()

    def id(self):
        raise NotImplementedError

    def path(self):
        raise NotImplementedError

    def print_build_info(self):
        print(
            c.act("Invoking"),
            c.name(self.module),
            c.act("template builder on"),
            c.name(self.target),
            c.path(os.path.join(*self.path())),
        )

    def create_context(self):
        self.context = self.root_context_class(os.path.realpath(self.args.launch), *self.id())

    def build(self):
        self.print_debug_info()
        self.print_build_info()

        for dir, templates in self.templates.items():
            for template in templates:
                jinja.print_template(os.path.join(self.template_root, dir), template, self.context.data, self.output_directory)

        print(c.ok("Template builder on"), c.name(self.target), c.ok("successful"))
