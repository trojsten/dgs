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
#: `mathematics`/`math`, `moment-inertia`/`moi` (now spelled `moment-of-inertia`),
#: `sound`/`acoustics`,
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
    'momentum': 'conservation of momentum, collisions, recoil',
    'com': 'centre of mass',
    'springs': 'springs and elasticity',
    'friction': 'friction between surfaces',
    'gforce': 'apparent weight, centrifugal and centripetal effects',
    'pendulum': 'pendulums',
    'pulleys': 'pulleys',
    'drag': 'resistance of a medium to motion through it',

    # -- rotation --------------------------------------------------------------------------------
    'rot-mech': 'rotational mechanics',
    'moment-of-inertia': 'moment of inertia',

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

    # == chemistry ===============================================================================
    # Chemistry Náboj had no vocabulary at all: every problem in volumes 01 to 04 carried either
    # no `tags:` key or the placeholder `['?']`. These cover all 144 of them. Physics tags are
    # shared where they already say the right thing -- `gases` for the state equation, `nuclear`
    # for decay, `calorimetry`, `mixing`, `buoyancy`, `geometry`, `math`, `units` -- so this block
    # adds only what chemistry needs and physics has no word for.

    # -- chemistry: the sub-disciplines, as a chemist would name them -----------------------------
    # Coarse, and deliberately so: they answer "which course is this from", which is the first
    # thing anyone browsing the archive wants, and they are the only tags that apply to a problem
    # whose actual content is a structure drawing.
    'inorganic': 'inorganic chemistry',
    'organic': 'organic chemistry',
    'analytical': 'analytical chemistry -- determining what and how much',
    'physical-chemistry': 'physical chemistry',
    'biochemistry': 'the chemistry of living things',

    # -- chemistry: how much of what -------------------------------------------------------------
    'stoichiometry': 'balancing an equation, or reasoning from its coefficients',
    'molar-mass': 'molar and relative atomic masses',
    'formula': 'deducing a formula from composition, mass loss or analysis',
    'yield': 'how much product a reaction actually gives',
    'concentration': 'the concentration of a solution, and converting between ways of stating it',

    # -- chemistry: solutions and equilibria -----------------------------------------------------
    'acid-base': 'acids, bases, pH and neutralisation',
    'buffer': 'a solution that resists a change of pH',
    'equilibrium': 'chemical equilibrium and its constant',
    'solubility': 'dissolving, saturation, and the solubility product',
    'redox': 'oxidation and reduction',
    'electrochemistry': 'electrolysis, cells, and electric current driving chemistry',
    'complex': 'coordination compounds and other host-guest binding',

    # -- chemistry: rates and energy -------------------------------------------------------------
    'kinetics': 'how fast a reaction goes',
    'thermochemistry': 'the heat a reaction takes or gives, and bond energies',
    'colligative': 'a property set by how many particles are dissolved, not by which',

    # -- chemistry: structure --------------------------------------------------------------------
    'atomic-structure': 'electron configuration, orbitals, quantum numbers',
    'crystallography': 'unit cells and lattices, and what they imply about density',
    'periodic-table': 'the table itself -- symbols, groups, trends',
    'isotopes': 'isotopes and isotopic composition',
    'stereochemistry': 'chirality, enantiomers, diastereomers, geometric isomers',
    'isomerism': 'counting isomers, or telling them apart',
    'structure-elucidation': 'deducing an unknown structure from the evidence',
    'synthesis': 'a synthetic route, and what it gives at each step',
    'mechanism': 'how a reaction proceeds, step by step',
    'radical': 'radical reactions',

    # -- chemistry: the methods themselves -------------------------------------------------------
    'titration': 'volumetric analysis -- titrating to an endpoint',
    'gravimetry': 'weighing before and after to find out what something is',
    'spectroscopy': 'absorbance and emission, the Beer-Lambert law',
    'nmr': 'nuclear magnetic resonance spectra',
    'chromatography': 'separating a mixture by how fast its parts travel',
    'qualitative': 'identifying a substance by what it does, not by measuring it',
    'lab-technique': 'the difficulty is in the practical procedure',
    'lab-safety': 'hazards, pictograms, and handling',

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
    'ordering': 'a list of items to be sorted, the answer being the order itself',
    # Both are shapes a problem takes, not subjects it is about, which is why they sit here with
    # `truth-or-dare` rather than among the chemistry topics that happen to use them most.
    'puzzle': 'a grid, crossword, word search or cipher wrapped around the chemistry',
    'matching': 'two lists to be paired up',
    'incorrect': 'the problem is wrong. Kept as it stands because it was used this way years ago '
                 '-- do not "fix" it',
}


def valid_tag(tag: str) -> bool:
    return tag in VALID_TAGS


class NabojStandaloneContext(renderer.StandaloneContext):
    _schema = renderer.StandaloneContext._schema | Schema({
        # Who did what, by role: `idea` is whoever thought of the problem, `problem`
        # whoever wrote the statement, `solution` whoever wrote up the solution. All three
        # are optional, so a problem records only what is known -- absent and empty both
        # mean unrecorded. Note the volume-level `authors` in `contexts/hierarchy.py` is a
        # different thing, listing people across the whole volume.
        'authors': {
            Opt('idea'): Or(list[str], []),
            Opt('problem'): Or(list[str], []),
            Opt('solution'): Or(list[str], []),
        },
        'tags': Or(list[And(str, valid_tag)], []),          # Tags
        # Editorial metadata a handful of problems carry. Nothing reads these yet, but the schema
        # admits no unknown key, so without them three problems fail to render at all rather than
        # merely being unannotated: `26/liquid-crane` (`difficulty`), `27/antifreeze` (`physics`,
        # `math`) and `27/half-g` (`similar`). `difficulty` and the `physics`/`math` pair look like
        # one idea before and after being split in two; `similar` points at a related problem id.
        # `tools/editor`'s audit page reads this: a list of check ids the problem opts out of,
        # for findings that are the point of the problem rather than a defect. `23/bats` and
        # `28/john-doe` have invented units on purpose; `23/grammar-nazi` is misspelled on purpose.
        Opt('audit'): {Opt('ignore'): [str]},
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
