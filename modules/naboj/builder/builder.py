import abc
from pathlib import Path

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

    def build_templates(self):
        super().build_templates()
        for template in self.i18n_templates:
            jinja.print_template(
                Path(self.launch_directory, *self.path()), template, self.context.data,
                outdir=self.output_directory,
                new_name=Path(template).with_suffix('.tex'),
            )
