import logging

from pathlib import Path

from .context import Context

log = logging.getLogger('dgs')


class FileContext(Context):
    """
    A Context that is loaded from a file (currently only YAML).
    """
    def __init__(self, new_id: str, path: Path, **defaults):
        super().__init__(new_id, **defaults)
        self.load_yaml(path)
