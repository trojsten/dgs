#!/usr/bin/env python
import logging

from abc import ABC


from enschema import Schema, Or, Optional as Opt, And

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
