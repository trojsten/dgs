import argparse
import logging
import os
import pprint
import subprocess
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import ClassVar

import argparsedirs

from core.builder.context import Context
from core.builder.products import Root, written
from core.builder.context.buildable import BuildableContext
from core.builder.jinja import JinjaRenderer
from core.utilities import colour as c
from core.utilities import crawler

log = logging.getLogger('dgs')


def empty_if_none(what) -> str:
    return '' if what is None else what


def check_output(command, *, cwd) -> str:
    return subprocess.check_output(command, cwd=cwd if cwd is not None else os.getcwd()).decode().rstrip("\n")


def get_last_commit_hash(cwd=None) -> str:
    return check_output(["git", "rev-parse", "--short", "--verify", "HEAD"], cwd=cwd)


def get_branch(cwd=None) -> str:
    return check_output(["git", "rev-parse", "--symbolic-full-name", "--abbrev-ref", "HEAD"], cwd=cwd)


def get_describe(cwd=None) -> str:
    """
    The version a human would quote: the tag if there is one, and the commit if there is not.

    `--tags` so that a lightweight tag counts -- `29-final` is one and `git describe` would
    otherwise ignore it; `--always` so a repository that has never been tagged still answers,
    with the short hash, which is what every one of these printed before there were tags;
    `--dirty` because a hash taken from a tree with uncommitted changes names a tree that was
    not built, and silence about that is the one thing a build stamp must not do.

    So `v5.0-458-gf948a98-dirty` reads as *458 commits past v5.0, at f948a98, and edited*, and
    `29-final` as *exactly that tag*, which is the one case where the hash is worth dropping:
    a reader can check the tag out by name.
    """
    return check_output(["git", "describe", "--tags", "--always", "--dirty"], cwd=cwd)


class BaseBuilder(metaclass=ABCMeta):
    """
    The abstract base class for all Builders. A Builder provides an abstraction for
    - reading and validating the content file system structures
    - reading and validating the templates
    - building the context tree (generally a subclass of Context)
    - rendering the context into the templates

    The script should only define and instantiate a builder, then run it with
    >>> class Builder(BaseBuilder):
    >>>     def add_arguments(self) -> None:
    >>>         ...
    >>>
    >>>     def ident(self) -> tuple[Any]:
    >>>         return self.year, self.issue
    >>>

    >>>
    >>> if __name__ == '__main__':
    >>>     Builder().build_templates()

    **Under `if __name__`, always.** Every builder here is run as `python -m <module>`, which
    sets `__main__`, so the guard costs nothing at build time -- and without it, merely
    *importing* a builder parses `sys.argv` and writes files. That is not hypothetical: the
    graph generator and the tests both want to ask a builder what it produces without running
    it, and the job runner's preload list had to be written around the old behaviour after an
    import printed an argparse usage message and took the daemon down.
    """
    module = None
    #: What this builder writes, as a `core.builder.products.Node`. The authority: the graph
    #: generator imports the same declaration instead of restating the list.
    _node = None
    _target: str = None
    _root_context_class: ClassVar[type[Context]] = None
    _renderer_class: ClassVar[type[JinjaRenderer]]

    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Build a dgs LaTeX template set from repository")
        self.add_core_arguments()
        self.add_arguments()
        self.args = self.parser.parse_args()

        log.setLevel(logging.DEBUG if self.args.debug else logging.INFO)
        self.launch_directory = Path(self.args.launch)
        self.template_root = Path(self.args.template_root)
        self.output_directory = Path(self.args.output) if self.args.output else None
        self.context = self._root_context_class(self.launch_directory, *self.ident())

        self.renderer = self._renderer_class(Path(self.template_root))

    def add_core_arguments(self) -> None:
        """ Create the default ArgumentParser """
        self.parser.add_argument('launch', action=argparsedirs.ReadableDir)
        self.parser.add_argument('template_root', action=argparsedirs.ReadableDir)
        self.parser.add_argument('-o', '--output', action=argparsedirs.WriteableDir)
        self.parser.add_argument('-d', '--debug', action='store_true')
        self.parser.add_argument('-t', '--tree', action='store_true')

    @abstractmethod
    def add_arguments(self) -> None:
        """ Add extra arguments for specific builders """

    def full_name(self) -> str:
        """ Full name of the builder for log reporting """
        return '/'.join(map(str, self.ident()))

    def full_path(self) -> Path:
        """ Full path of the builder """
        return Path(self.launch_directory, *self.path())

    @abstractmethod
    def ident(self) -> tuple[str]:
        """ Return the id tuple """

    @abstractmethod
    def path(self) -> tuple[str]:
        """ Return the root path for this builder """

    def print_debug_info(self) -> None:
        """ Prints debug info """
        log.debug(c.act("Content templates:"))
        pprint.pprint(self.templates)

        log.debug(c.act(f"Context ({self.context.__class__.__qualname__}):"))
        self.context.print()

        log.debug(c.act("Schema:"))
        print(self.context.schema)

    def print_build_info(self) -> None:
        """ Prints build info for progress reports """
        log.info(f"{c.act('Invoking')} {c.name(self.module)} {c.act('template builder on')} "
                 f"{c.meta(self._target)} {c.name(self.full_name())} at {c.path(self.full_path())}")

    def print_dir_info(self) -> None:
        """ Prints directory tree info (probably only useful for debugging) """
        log.debug(f"{c.act('Directory structure:')}")
        crawler.Crawler(Path(self.launch_directory, *self.path())).print_path()

    # **No `output_path`.** It derived a `.tex` name from a `.jtex` one through a `suffix_map`,
    # and `build_templates` stopped calling it when a product started stating its own `suffix`
    # -- `core/builder/products.py` says why the two genuinely differ, `crossref.jyaml` being
    # written out as `<language>.yaml`. It survived the refactor with no caller, which is the
    # shape a helper rots in: present, plausible, and no longer the authority for anything.

    def roots(self) -> dict[Root, Path]:
        """
        Where each kind of product's template is resolved. One entry per `Root` the node uses.

        This is the half of `written()` only the caller knows: the builder is standing in the
        node, the graph generator is standing outside it, and the predicate they share is the
        same. A subclass that declares a product rooted anywhere but `TEMPLATES` adds the entry
        here.
        """
        return {Root.TEMPLATES: Path(self.template_root)}

    def product_ident(self) -> str:
        """What `{ident}` in a product name interpolates to. Only a renaming node needs it."""
        return ''

    def build_templates(self) -> None:
        """
        Write every product this node declares, in declaration order.

        One loop, where there used to be one per root -- `BaseBuilder` rendered the module's
        templates, `BuilderNaboj` added the node's own, `BuilderNabojVenue` a third from the
        language directory -- and the three differed only in which directory they rendered from.
        `core/builder/products.py` has the seam this draws.

        **Rendered before the target is opened.** `open(..., 'w')` truncates at once, so a
        template that raises used to leave a 0-byte `.tex` behind, which a build then treats as
        up to date and never rebuilds. Two of the three loops had learned that and this one is
        the merge of all three, so it keeps it.
        """
        assert isinstance(self.context, BuildableContext), \
            c.err(f"Builder's context class is {self.context.__class__.__name__}, which is not a buildable context!")
        assert self._node is not None, \
            c.err(f"{self.__class__.__name__} declares no node; see core/builder/products.py")

        self.print_build_info()

        if self.args.debug:
            self.print_debug_info()

        if self.args.tree:
            self.print_dir_info()

        roots = self.roots()
        ident = self.product_ident()
        due = written(self._node, roots)
        for product in self._node.products:
            if product not in due:
                log.warning(f"No {c.path(product.template)} for "
                            f"{c.name('/'.join(str(p) for p in self.path()))}, skipping it")
        renderers = {}
        for product in due:
            if product.root not in renderers:
                renderers[product.root] = self._renderer_class(roots[product.root])
            rendered = renderers[product.root].render(Path(product.template), self.context.data)
            with open(self.output_directory / product.filename(ident), 'w') as outfile:
                print(rendered, file=outfile)

        log.debug(f"{c.ok('Template builder on')} {c.name(self._target)} "
                  f"{c.path(self.full_name())} {c.ok('successful')}")
