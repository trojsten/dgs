"""
What one invocation of a builder writes -- declared once, consumed by the builder and the graph.

**The seam this exists to draw.** A builder declares the set of files one invocation of it writes,
as a pure function of the paths it is given. The graph declares everything else: which of those
files go on to another tool, what each one reads, and what human-typed name aggregates them. The
operational test, for whoever adds the next module: *if you could learn it by running the builder
and listing `<outdir>`, it is the builder's; if you could only learn it by reading a template or a
recipe, it is the graph's.*

Before this, both sides knew the first half and neither was the authority. `language.py` listed
nine templates and `tools/ninja/generate.py` listed the same nine as `LANGUAGE_DOCUMENTS`, with a
comment naming the builder as the authority it was copying. The same for the venue's two, the
seminar round's four and scholar's five. Worse, the rule *"this output exists only when its source
does"* was written twice in two shapes -- the builder skipped a missing template with a warning,
the generator probed the filesystem before declaring the output -- and a template then assumed the
file was there regardless. Three layers each encoding the same optionality, and the bug lived in
the one that did not: `instructions.jtex` used a bare `\\input` for a venue's
`instructions-inner.tex`, so adding a venue to a volume with no instructions in any language
turned the build red with nothing saying what was missing.

**`written()` is the whole mechanism.** The builder's skip and the graph's probe are now the same
call against the same declaration; only the root map differs, because only the caller knows where
it is standing.

Stdlib only, deliberately. A declaration is imported by the graph generator, by the tests and
(transitively) by the builders, and the generator has no business dragging in pint, jinja2 and the
validation machinery to ask a module what it writes. `modules/` and `modules/<module>/` carry no
`__init__.py`, so importing one executes exactly that one file.
"""
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Root(StrEnum):
    """
    Which directory a product's template is resolved against.

    Three, because the three loops this replaced differed in exactly this and nothing else:
    `BaseBuilder` rendered from the module's template root, `BuilderNaboj` added a loop rooted at
    the node's own source directory, and `BuilderNabojVenue` a third rooted at a *sibling* node's
    language directory. One loop over products, each carrying the root it wants.
    """
    #: `modules/<module>/templates/` -- the module's own templates, the same for every node.
    TEMPLATES = 'templates'
    #: The node's own source directory, `source/<module>/<path()>`.
    UNIT = 'unit'
    #: A related node's directory. Náboj's venue alone: its `instructions-inner.jtex` lives in the
    #: *language* the venue is run in, which is a sibling of the venue, not a child.
    LANGUAGE = 'language'


@dataclass(frozen=True)
class Product:
    """One file a builder writes, and the template it comes from."""

    #: The output's stem. `{ident}` interpolates the builder's `product_ident()`, which is how
    #: `core/builder/i18n.py` writes `override.jtex` out as `<language>.tex`; everything else
    #: names itself after its template and leaves the hook alone.
    name: str
    #: Resolved against `root`, and passed to the renderer bare.
    template: str
    root: Root = Root.TEMPLATES
    #: Written only when the template is actually there. **Never true for a `TEMPLATES` product**
    #: -- a module template that is missing is a bug and must still raise, not vanish quietly.
    #: `core/tests/test_declarations.py` asserts that over every declaration in the repository.
    optional: bool = False
    #: Not derived from the template's own suffix, because the two genuinely differ:
    #: `crossref.jyaml` is written out as `<language>.yaml`.
    suffix: str = '.tex'

    def filename(self, ident: str = '') -> str:
        return f'{self.name.format(ident=ident)}{self.suffix}'


@dataclass(frozen=True)
class Node:
    """Everything one invocation of one builder writes. `target` is what the build calls it."""
    target: str
    products: tuple[Product, ...]

    def names(self) -> tuple[str, ...]:
        """Every product's stem, declared or not. What the graph checks its PDF lists against."""
        return tuple(product.name for product in self.products)


def written(node: Node, roots: dict[Root, Path]) -> list[Product]:
    """
    The products one invocation writes, given the directories it would run against.

    Order is the declaration's, and that is load-bearing rather than tidy: the loops this replaced
    rendered the module's templates first and the node's own second, and a template that reads a
    file a sibling has just written would see the difference. Declare them in the order they are
    to be rendered.

    A caller that cannot supply a root need not: a root is only consulted for an `optional`
    product, so a map missing `Root.LANGUAGE` is fine for a node that has no language products.
    """
    out = []
    for product in node.products:
        if product.optional:
            root = roots.get(product.root)
            if root is None or not (Path(root) / product.template).is_file():
                continue
        out.append(product)
    return out


def read_scalar(meta: Path, key: str) -> str | None:
    """
    One top-level scalar out of a YAML file, by line scan, without a parser.

    For the handful of facts the build graph needs *before* anything has built a context: which
    language a venue's documents are set in, which language a monolingual scope is written in.
    A parse would be more correct in general and is the wrong tool here -- a declaration is
    imported by the generator, by the builders and by the tests, and should not pull a YAML
    library in to read one key. Every such key is a plain scalar and the schema requires it to
    be one, so there is no YAML to get wrong.

    An inline comment and surrounding quotes are stripped; an empty value reads as absent. The
    guess is not trusted blindly -- `core/tests/test_declarations.py` pins it against the
    context that is the real authority.
    """
    try:
        text = meta.read_text(encoding='utf-8')
    except OSError:
        return None
    for line in text.splitlines():
        name, separator, value = line.partition(':')
        # **Top level only.** `name.strip() == key` would take an indented one too, and that is
        # not pedantry: `fks-naboj/20/venues/bratislava/meta.yaml` carries no `language:` of its
        # own and a `language: slovak` on every entry of its `teams:` list, so the loose test
        # reads the first team's language as the venue's. Nothing builds that tree, which is why
        # it survived -- but a nested key is the one way this scan can be confidently wrong, and
        # the whole reason it is allowed to exist is that it cannot be.
        if separator and name == key and (found := value.split('#')[0].strip().strip('\'"')):
            return found
    return None
