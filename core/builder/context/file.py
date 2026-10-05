import logging
from pathlib import Path

from .context import Context

log = logging.getLogger('dgs')


class FileContext(Context):
    """
    A Context that is loaded from a file (currently only YAML).

    `text` overrides what the file holds while keeping `path` as the identity -- an unsaved
    buffer, which is what `tools/editor` previews from. Everything downstream sees an ordinary
    context, so a preview and a build cannot read the meta differently.
    """
    def __init__(self, new_id: str, path: Path, *, text: str | None = None, **defaults):
        super().__init__(new_id, **defaults)
        if text is None:
            self.load_yaml(path)
        else:
            self.load_string(text)
