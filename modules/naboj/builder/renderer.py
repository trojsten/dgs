#!/usr/bin/env python
import argparse
import io
import numbers
import pprint
import shutil
import logging

from abc import ABC
from io import TextIOWrapper, StringIO

from pathlib import Path
from tempfile import SpooledTemporaryFile, NamedTemporaryFile
from typing import Optional

from enschema import Schema, Or, Optional as Opt, And

from core.builder.context.context import Context
from core.builder.context.file import FileContext
from core.builder.jinja import MarkdownJinjaRenderer

from core.builder.context.quantities import PhysicsConstant
from core.utilities import colour as c
import renderer

log = logging.getLogger('dgs')


VALID_TAGS: dict[str, str] = {
    'kinematics': 'kinematics',
    'statics': 'statics',
    'electrostatics': 'electrostatics',
    'nuclear': 'nuclear physics',
    'relativity': 'special or general relativity',
    'uam': 'uniformly accelerated motion',
    'com': 'centre of mass',
    'creative': 'a problem that requires out-of-the-box thinking',
    'thermodynamics': 'thermodynamics',
    'hydrostatics': 'hydrostatics',
    'hydrodynamics': 'hydrodynamics',
    'buoyancy': 'buoyancy',
    'troll': 'a problem with a trivial solution',
    'elegant': 'short but interesting problem',
}



def valid_tag(tag: str) -> bool:
    return tag in VALID_TAGS


class JinjaConvertor:
    def __init__(self,
                 template: TextIOWrapper,
                 outfile: Optional[TextIOWrapper],
                 *,
                 context: Context,
                 preamble: Optional[io.TextIOWrapper] = None,
                 preamble_prepend: Optional[str] = '',
                 debug: bool = False):
        self.outfile: Optional[Path] = outfile
        self.context: Context = context

        with SpooledTemporaryFile(mode="w+") as tmp:
            # If there is a preamble, prepend it to the actual file
            if preamble is not None:
                # FixME prepend preamble_prepend to every line (default '@J set ')
                shutil.copyfileobj(preamble, tmp)

            # Always copy the actual template
            shutil.copyfileobj(template, tmp)
            tmp.seek(0)

            if debug:
                log.debug(f"{c.debug('Template to render into')}:")
                print(tmp.read())
                tmp.seek(0)

                log.debug(f"{c.debug('Context data')}:")
                pprint.pprint(context.data)

            self.renderer = MarkdownJinjaRenderer(template=tmp.read())

    def run(self):
        self.renderer.render(self.context.data, outfile=self.outfile)
        return 0


class NabojStandaloneContext(renderer.StandaloneContext):
    _schema = renderer.StandaloneContext._schema | Schema({
        'authors': list[str],                       # List of authors
        'tags': list[And(str, valid_tag)],          # Tags
    })


class CLIInterface(renderer.CLIInterface, ABC):
    """
    Jinja CLI interface
    """
    description = "dgs Jinja Náboj convertor"
    context_cls = NabojStandaloneContext


if __name__ == "__main__":
    CLIInterface().run()
