#!/usr/bin/env python
"""
Build the standalone one-problem document for a single seminar problem.

Modelled on `modules.naboj.builder.standalone`, and lean for the same reason: the context is a
handful of strings taken from the path, so there is no volume to validate and no repository tree
to walk. A preview has to build for a problem whose round or semester does not.
"""
import argparse
from pathlib import Path

import argparsedirs
import yaml

from core.builder.context import Context
from core.builder.jinja import StaticRenderer

TEMPLATE = 'standalone.jtex'


def read_yaml(path: Path) -> dict:
    """Whatever the file holds, or nothing -- a half-written meta.yaml must not stop a preview."""
    try:
        return yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return {}


def build(launch: Path, unit: str, output: Path, template_root: Path) -> None:
    competition, volume, semester, round_, number = unit.split('/')
    unit_path = Path(launch) / unit

    context = Context(
        unit,
        module='seminar',
        unit=unit,
        competition={'id': competition},
        volume=volume,
        semester=semester,
        round=round_,
        number=number,
        # `sk` for every seminar there has ever been, but read it rather than assume it.
        language=read_yaml(Path(launch) / competition / 'meta.yaml').get('language', 'sk'),
        # The booklet heads a problem with its title; fall back to the directory name, which is
        # what an unconverted or brand new problem has instead.
        title=read_yaml(unit_path / 'meta.yaml').get('title') or number,
    )
    outfile = Path(output) / Path(TEMPLATE).with_suffix('.tex')
    with open(outfile, 'w') as f:
        print(StaticRenderer(Path(template_root)).render(Path(TEMPLATE), context.data), file=f)


def main():
    parser = argparse.ArgumentParser(description="Build a standalone one-problem seminar document")
    parser.add_argument('unit', type=str, help="path of the problem below source/seminar/")
    parser.add_argument('-o', '--output', action=argparsedirs.WriteableDir, required=True)
    parser.add_argument('-t', '--template-root', action=argparsedirs.ReadableDir,
                        default='modules/seminar/templates/')
    parser.add_argument('-l', '--launch', action=argparsedirs.ReadableDir, default='source/seminar/')
    args = parser.parse_args()
    build(Path(args.launch), args.unit, Path(args.output), Path(args.template_root))


if __name__ == '__main__':
    main()
