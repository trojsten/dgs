#!/usr/bin/env python
"""
Build the standalone one-problem document (`standalone.jtex`) for a single problem
in a single language.

Modelled on `core.builder.standalone.BuilderStandalone` rather than on `BaseBuilder`:
the whole context is five strings taken from the path, so there is no `meta.yaml` to
read, no schema to satisfy, no `validate_repo()` and no `git rev-parse`. That is the
point -- a preview has to build for a problem whose volume does not, which is most of
them at any given moment (an incomplete `languages/` tree, a `meta.yaml` that has not
been converted yet, a missing `evaluators.jtex`).

Note there is no `launch` argument, unlike the language and venue builders: nothing
here is read from `source/`.
"""
import argparse
from pathlib import Path

import argparsedirs

from core.builder.context import Context
from core.builder.jinja import StaticRenderer


class BuilderNabojStandalone:
    template = 'standalone.jtex'

    def __init__(self,
                 competition: str,
                 volume: int,
                 problem: str,
                 language: str,
                 output_directory: Path,
                 template_root: Path):
        self.output_directory = Path(output_directory)
        self.context = Context(
            f'{competition}/{volume:02d}/{problem}/{language}',
            module={'id': 'naboj'},
            competition={'id': competition},
            volume={'id': f'{volume:02d}'},
            problem={'id': problem},
            language={'id': language},
        )
        self.renderer = StaticRenderer(Path(template_root))

    def run(self) -> None:
        outfile = self.output_directory / Path(self.template).with_suffix('.tex')
        with open(outfile, 'w') as f:
            print(self.renderer.render(Path(self.template), self.context.data), file=f)


def main():
    parser = argparse.ArgumentParser(description="Build a standalone one-problem Náboj document")
    parser.add_argument('competition', choices=['phys', 'math', 'chem', 'junior', 'test'])
    parser.add_argument('volume', type=int)
    parser.add_argument('problem', type=str)
    parser.add_argument('language', type=str)
    parser.add_argument('-o', '--output', action=argparsedirs.WriteableDir, required=True)
    parser.add_argument('-t', '--template-root', action=argparsedirs.ReadableDir,
                        default='modules/naboj/templates/')
    args = parser.parse_args()

    BuilderNabojStandalone(args.competition, args.volume, args.problem, args.language,
                           args.output, args.template_root).run()


if __name__ == '__main__':
    main()
