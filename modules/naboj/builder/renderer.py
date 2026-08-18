#!/usr/bin/env python
import logging
from abc import ABC

from enschema import And, Or, Schema
from enschema import Optional as Opt

from core.builder import renderer

log = logging.getLogger('dgs')


#: Every tag a problem may carry, with what it means. Grouped by area, and complete: it covers all
#: 363 tag uses in volumes 25 to 29, which between them hold the whole vocabulary.
#:
#: This list used to name 14 tags while 62 were in use, because `valid_tag` never actually ran --
#: enschema does not check the elements of `list[And(str, valid_tag)]` -- so nothing stopped a new
#: spelling from being invented. Twelve pairs had drifted apart that way and have been merged:
#: `mathematics`/`math`, `moment-inertia`/`moi`, `sound`/`acoustics`,
#: `unit-conversions`/`units`, `thermo`/`thermodynamics`, `tricky`/`trick`,
#: `archimedes`/`buoyancy`, `cog`/`com`, `snell`/`refraction`, `liquids`/`hydrodynamics`,
#: `paaa`/`oblique-throw`, and `electicity`, a typo for `electricity`.
VALID_TAGS: dict[str, str] = {
    # -- kinematics ------------------------------------------------------------------------------
    'kinematics': 'motion, in general',
    'uam': 'uniformly accelerated motion',
    'oblique-throw': 'a body thrown at an angle in a homogeneous gravitational field',
    'free-fall': 'released from rest and falling',
    'jerk': 'jerk, the time derivative of acceleration',

    # -- mechanics -------------------------------------------------------------------------------
    'statics': 'bodies in equilibrium',
    'dynamics': 'forces and the motion they cause',
    'energy': 'conservation of energy, work',
    'com': 'centre of mass',
    'springs': 'springs and elasticity',
    'friction': 'friction between surfaces',
    'gforce': 'apparent weight, centrifugal and centripetal effects',
    'pendulum': 'pendulums',
    'pulleys': 'pulleys',
    'drag': 'resistance of a medium to motion through it',

    # -- rotation --------------------------------------------------------------------------------
    'rot-mech': 'rotational mechanics',
    'moi': 'moment of inertia',

    # -- fluids ----------------------------------------------------------------------------------
    'buoyancy': 'buoyancy',
    'hydrostatics': 'liquids at rest',
    'hydrodynamics': 'liquids in motion',

    # -- thermal ---------------------------------------------------------------------------------
    'thermodynamics': 'thermodynamics',
    'calorimetry': 'heat exchange, specific and latent heat',
    'gases': 'the ideal gas and its state equation',
    'thermo-process': 'a named process: isothermal, adiabatic and the rest',
    'mixing': 'mixing substances at different temperatures or concentrations',
    'blackbody': 'thermal radiation, the Stefan-Boltzmann law',

    # -- electromagnetism ------------------------------------------------------------------------
    # `electricity` is the umbrella -- electrostatics, electrodynamics, all of it -- and `circuit`
    # is the narrower one, about Kirchhoff's laws and the like. They may overlap.
    'electricity': 'electric phenomena of any kind',
    'circuit': "circuits, Kirchhoff's laws",
    'resistance': 'resistance and resistor networks',
    'electrostatics': 'charges at rest',
    'elmag': 'magnetism and electromagnetic induction',

    # -- optics and waves ------------------------------------------------------------------------
    'optics': 'light, mirrors, lenses',
    'refraction': 'refraction at an interface',
    # Dispersion only. It used to carry thermal radiation too, which is now `blackbody`.
    'spectrum': 'dispersion, light split into its components',
    'acoustics': 'sound',

    # -- gravity and astronomy -------------------------------------------------------------------
    'gravity': 'gravitational fields and forces',
    'orbital-mechanics': 'orbits',
    'relativity': 'special or general relativity',

    # -- modern ----------------------------------------------------------------------------------
    'nuclear': 'nuclear physics',

    # -- method rather than topic ----------------------------------------------------------------
    'geometry': 'the difficulty is geometric',
    'math': 'the difficulty is mathematical',
    'units': 'units, dimensions and conversions between them',
    'trigonometry': 'trigonometric identities do the work',
    'spherical-geometry': 'geometry on the surface of a sphere',
    'fractal': 'self-similarity, an infinite series of ever smaller copies',

    # -- flavour, not physics --------------------------------------------------------------------
    # These describe what kind of problem it is, and several are load-bearing: `incorrect` in
    # particular is a warning, not a topic.
    'creative': 'requires out-of-the-box thinking',
    'elegant': 'short but interesting',
    'trick': 'a neat trick solves it easily, though the result is serious',
    'troll': 'a complex or outright scary statement that boils down to something very simple, '
             'usually answering 0 or 1',
    'silly': 'something silly in the story; the physics is sound',
    'unreal': 'the physics does not model the real world, but is still computable as stated',
    'truth-or-dare': 'a list of statements to be judged true or false',
    'incorrect': 'the problem is wrong. Kept as it stands because it was used this way years ago '
                 '-- do not "fix" it',
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
