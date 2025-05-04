from abc import abstractmethod, ABC

from .context import Context
from .tree import FileSystemTreeContext


class BuildableContext(Context):
    """
    Only some contexts are meant to be built. This class provides a common ancestor.
    Currently only useful for sanity checks.
    """

    def __init__(self, root, *args, **kwargs):
        super().__init__(root)

    @abstractmethod
    def populate(self, *args, **kwargs):
        pass


class BuildableFileSystemTreeContext(FileSystemTreeContext, BuildableContext, ABC):
    def __init__(self, root, *path, **defaults):
        super().__init__(root, *path, **defaults)
        # A filesystem context needs to validate its repository upon creation
        self.validate_repo(*path)
