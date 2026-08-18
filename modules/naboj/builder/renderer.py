#!/usr/bin/env python
import logging
from abc import ABC

from enschema import And, Or, Schema
from enschema import Optional as Opt

from core.builder import renderer

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
        'authors': Or(list[str], []),             # List of authors
        'tags': Or(list[And(str, valid_tag)], []),          # Tags
        # Editorial metadata a handful of problems carry. Nothing reads these yet, but the schema
        # admits no unknown key, so without them three problems fail to render at all rather than
        # merely being unannotated: `26/liquid-crane` (`difficulty`), `27/antifreeze` (`physics`,
        # `math`) and `27/half-g` (`similar`). `difficulty` and the `physics`/`math` pair look like
        # one idea before and after being split in two; `similar` points at a related problem id.
        Opt('difficulty'): int,
        Opt('physics'): int,
        Opt('math'): int,
        Opt('similar'): Or(list[str], []),
    })


class CLIInterface(renderer.CLIInterface, ABC):
    """
    Jinja CLI interface
    """
    description = "dgs Jinja Náboj convertor"
    context_cls = NabojStandaloneContext


if __name__ == "__main__":
    CLIInterface().run()
