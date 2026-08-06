#!/usr/bin/env python
import datetime
import logging

from enschema import Optional, Or, Schema

from core.builder import renderer

log = logging.getLogger('dgs')


class ScholarStandaloneContext(renderer.StandaloneContext):
    """
    Scholar's front matter, as its sources actually carry it.

    The schema used to require `title` and permit nothing else, which matched 25 of the ~160
    meta.yaml files in the tree: 43 are empty, 27 pair `title` with a `date`, 26 carry a homework
    `deadline`, 26 a `name` and two a `bonus` flag. Every other unit failed to render at all. The content is the
    source of truth here -- it predates the schema -- so the schema follows it.
    """
    _schema = renderer.StandaloneContext._schema | Schema({
        Optional('title'): str,
        Optional('name'): str,
        Optional('date'): Or(datetime.date, str),
        Optional('deadline'): Or(datetime.date, str),
        Optional('bonus'): bool,
    })


class CLIInterface(renderer.CLIInterface):
    """
    Jinja CLI interface
    """
    description = "dgs Jinja Náboj convertor"
    context_cls = ScholarStandaloneContext


if __name__ == "__main__":
    CLIInterface().run()
