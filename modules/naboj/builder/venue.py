import logging
from pathlib import Path

from core.builder.products import Root
from modules.naboj import declaration
from modules.naboj.builder.builder import BuilderNaboj
from modules.naboj.builder.contexts import BuildableContextVenue

log = logging.getLogger('dgs')


class BuilderNabojVenue(BuilderNaboj):
    _target = 'venue'
    _subdir = 'venues'

    _root_context_class = BuildableContextVenue
    _node = declaration.VENUE

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('venue', type=str)

    def ident(self) -> tuple:
        return self.args.competition, self.args.volume, self.args.venue

    def path(self) -> tuple:
        return self.args.competition, f'{self.args.volume:02d}', self._subdir, self.args.venue

    def language_path(self) -> tuple:
        return self.args.competition, f'{self.args.volume:02d}', 'languages', self.context.data['language']['id']

    def roots(self):
        """
        Adds the venue's *language* directory, which is a sibling node rather than a child.

        It is the one root in the repository a context computes: the language comes from the
        venue's own validated meta, so it is not knowable from the path alone. The graph cannot
        call this -- it builds no contexts -- and reads the key itself through
        `modules.naboj.declaration.venue_language`, which `core/tests/test_declarations.py` pins
        against this.

        `launch_directory`, not a path with this machine's home in it: the absolute
        `/home/kvik/dgs/source/naboj` that used to be here meant the venue builder could only
        ever run on one computer, and `-l/--launch` is exactly the knob for it.
        """
        return super().roots() | {Root.LANGUAGE: Path(self.launch_directory, *self.language_path())}


if __name__ == '__main__':
    BuilderNabojVenue().build_templates()
