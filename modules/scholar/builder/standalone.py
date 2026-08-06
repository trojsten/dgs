#!/usr/bin/env python
"""
Build the standalone one-unit document for a single scholar unit.

Two things are editable here and they are different shapes: a handout or homework sheet, which
holds its own `text.md`, and a problem inside one, which holds `problem.md` and `solution.md`.
Both preview through this template; only the list of parts differs, and that follows from the
depth of the path.

Lean for the same reason as its Náboj and seminar counterparts: the context is a few strings
taken from the path, so a preview builds for a sheet whose meta.yaml does not yet validate --
and scholar's currently do not.
"""
import argparse
from pathlib import Path

import argparsedirs
import yaml

from core.builder.context import Context
from core.builder.jinja import StaticRenderer

TEMPLATE = 'standalone.jtex'

# `<course>/<year>/<kind>/<issue>` is the sheet itself; a fifth segment is a problem inside it.
SHEET_DEPTH = 4


def read_yaml(path: Path) -> dict:
    """Whatever the file holds, or nothing -- a half-written meta.yaml must not stop a preview."""
    try:
        return yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return {}


def build(launch: Path, unit: str, output: Path, template_root: Path) -> None:
    segments = unit.split('/')
    course = segments[0]
    unit_path = Path(launch) / unit
    meta = read_yaml(unit_path / 'meta.yaml')

    context = Context(
        unit,
        module='scholar',
        unit=unit,
        course=course,
        language=read_yaml(Path(launch) / course / 'meta.yaml').get('language', 'sk'),
        parts=['text'] if len(segments) == SHEET_DEPTH else ['problem', 'solution'],
        # Sheets carry a title; individual problems mostly do not, so fall back to the directory
        # name, which is what the author is looking at in the picker anyway.
        title=meta.get('title') or segments[-1],
    )
    outfile = Path(output) / Path(TEMPLATE).with_suffix('.tex')
    with open(outfile, 'w') as f:
        print(StaticRenderer(Path(template_root)).render(Path(TEMPLATE), context.data), file=f)


def main():
    parser = argparse.ArgumentParser(description="Build a standalone one-unit scholar document")
    parser.add_argument('unit', type=str, help="path of the unit below source/scholar/")
    parser.add_argument('-o', '--output', action=argparsedirs.WriteableDir, required=True)
    parser.add_argument('-t', '--template-root', action=argparsedirs.ReadableDir,
                        default='modules/scholar/templates/')
    parser.add_argument('-l', '--launch', action=argparsedirs.ReadableDir, default='source/scholar/')
    args = parser.parse_args()
    build(Path(args.launch), args.unit, Path(args.output), Path(args.template_root))


if __name__ == '__main__':
    main()
