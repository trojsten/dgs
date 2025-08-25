import abc
from pathlib import Path
from typing import Optional

from core.builder import builder
from core.builder.jinja import StaticRenderer


class BuilderNaboj(builder.BaseBuilder, metaclass=abc.ABCMeta):
    """
    The Builder for the Náboj competitions.
    """
    module: str = 'naboj'
    i18n_templates: list[str] = []

    _renderer_class = StaticRenderer

    def __init__(self):
        super().__init__()
        self.renderer = StaticRenderer(Path(self.template_root))

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('competition', choices=['phys', 'math', 'chem', 'junior', 'test'])
        self.parser.add_argument('volume', type=int)

    def build_templates(self, *, new_name: Optional[str] = None) -> None:
        super().build_templates()

        renderer = StaticRenderer(Path(self.launch_directory, *self.path()))

        for template in self.i18n_templates:
            outfile = open(self.output_directory / Path(template).with_suffix('.tex'), 'w')
            renderer.render(Path(template), self.context.data, outfile=outfile)
