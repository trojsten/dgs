import abc
import logging
from pathlib import Path

from core.builder.builder import BaseBuilder
from core.builder.jinja import StaticRenderer
from core.builder.products import Root
from modules.naboj import declaration

log = logging.getLogger('dgs')


class BuilderNaboj(BaseBuilder, metaclass=abc.ABCMeta):
    """
    The Builder for the Náboj competitions.
    """
    module: str = 'naboj'

    _renderer_class = StaticRenderer

    def __init__(self):
        super().__init__()
        self.renderer = self._renderer_class(Path(self.template_root))

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('competition', choices=declaration.COMPETITIONS)
        self.parser.add_argument('volume', type=int)

    def roots(self):
        """Adds the node's own source directory: Náboj's `intro` and `evaluators` live there."""
        return super().roots() | {Root.UNIT: Path(self.launch_directory, *self.path())}
