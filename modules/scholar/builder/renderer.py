#!/usr/bin/env python
import logging

from enschema import Schema

from core.builder import renderer

log = logging.getLogger('dgs')


class ScholarStandaloneContext(renderer.StandaloneContext):
    _schema = renderer.StandaloneContext._schema | Schema({
        'title': str,
    })


class CLIInterface(renderer.CLIInterface):
    """
    Jinja CLI interface
    """
    description = "dgs Jinja Náboj convertor"
    context_cls = ScholarStandaloneContext


if __name__ == "__main__":
    CLIInterface().run()
