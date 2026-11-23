"""
What core's own builder writes. See `core/builder/products.py` for the seam.
"""
from core.builder.products import Node, Product

#: `core/builder/i18n.py`, and the one node in the repository whose outputs are **renamed**: one
#: invocation per language writes `<language>.tex` and `<language>.yaml`, not `override.tex` and
#: `crossref.yaml`. That is what `{ident}` and the explicit `suffix` are for, and declaring it
#: here is what retired `build_templates(new_name=...)` -- a keyword that existed for this one
#: case and that the graph had no way to know about.
#:
#: Two outputs on one edge, and both are wanted: the booklet `\\input`s the `.tex` and every
#: pandoc run reads the `.yaml` as `crossrefYaml`. Make declared only the first, which left
#: `core/templates/crossref.jyaml` a prerequisite of nothing at all.
I18N = Node('global i18n', (
    Product('{ident}', 'override.jtex'),
    Product('{ident}', 'crossref.jyaml', suffix='.yaml'),
))

NODES = {'i18n': I18N}
