"""
What seminar's builder writes. See `core/builder/products.py` for the seam and why this is a
module of its own rather than an attribute on the builder class.
"""
from core.builder.products import Node, Product

#: `modules/seminar/builder/round.py`. All four come from the module's own templates -- seminar
#: is monolingual and a round has no per-language directory for an optional product to live in.
#:
#: `instagram` is built and is deliberately not among the PDFs the graph's `all` asks for: it is
#: one page per problem for a different medium, wanted on request. Make read it the same way --
#: its line in the round aggregate was commented out.
ROUND = Node('round', (
    Product('problems', 'problems.jtex'),
    Product('solutions', 'solutions.jtex'),
    Product('solutions-full', 'solutions-full.jtex'),
    Product('instagram', 'instagram.jtex'),
))

NODES = {'round': ROUND}
