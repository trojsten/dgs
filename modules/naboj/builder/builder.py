import abc
import logging
from pathlib import Path

import core.utilities.colour as c
from core.builder.builder import BaseBuilder
from core.builder.jinja import StaticRenderer

log = logging.getLogger('dgs')


class BuilderNaboj(BaseBuilder, metaclass=abc.ABCMeta):
    """
    The Builder for the Náboj competitions.
    """
    module: str = 'naboj'
    i18n_templates: list[str] = []

    _renderer_class = StaticRenderer

    def __init__(self):
        super().__init__()
        self.renderer = self._renderer_class(Path(self.template_root))

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('competition', choices=['phys', 'math', 'chem', 'junior', 'test'])
        self.parser.add_argument('volume', type=int)

    def build_templates(self, *, new_name: str | None = None) -> None:
        super().build_templates()

        # Also build files that are defined for a translation
        source_root = Path(self.launch_directory, *self.path())
        renderer = StaticRenderer(source_root)

        for template in self.i18n_templates:
            # `NabojValidator` marks `evaluators.jtex` optional and `module.mk` reaches for it
            # through `$(wildcard ...)`, but this loop used to render it unconditionally, so a
            # language without one died on `TemplateNotFound` and could not build at all -- not
            # even its tearoffs. Volume 26's `cs`, `es`, `hu` and `pl` are exactly that case.
            # Only `evaluation.pdf` and the venue `answers-modulo` read the result, so skipping
            # it costs nothing else.
            if not (source_root / template).exists():
                log.warning(f"No {c.path(template)} for {c.name('/'.join(str(p) for p in self.path()))}, "
                            f"skipping it")
                continue

            # Render before opening the target: `open(..., 'w')` truncates immediately, so a
            # template that raises used to leave a 0-byte `.tex` behind, which make then treats
            # as up to date and never rebuilds.
            rendered = renderer.render(Path(template), self.context.data)
            with open(self.output_directory / Path(template).with_suffix('.tex'), 'w') as outfile:
                print(rendered, file=outfile)
