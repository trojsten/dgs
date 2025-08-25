import abc
from pathlib import Path
from typing import Optional

from core.builder import builder
import core.builder.jinja as jinja


class BuilderNaboj(builder.BaseBuilder, metaclass=abc.ABCMeta):
    """
    The Builder for the Náboj competitions.
    """
    module: str = 'naboj'
    i18n_templates: [str] = []

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('competition', choices=['phys', 'math', 'chem', 'junior', 'test'])
        self.parser.add_argument('volume', type=int)

    def build_templates(self, *, new_name: Optional[str] = None) -> None:
        super().build_templates()

        renderer = jinja.StaticRenderer(Path(self.launch_directory, *self.path()))

        for template in self.i18n_templates:
            outfile = open(self.output_directory / Path(template).with_suffix('.tex'), 'w')
            renderer.render(Path(template), self.context.data, outfile=outfile)
