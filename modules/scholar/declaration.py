"""
What scholar's builders write. See `core/builder/products.py` for the seam.

Two nodes, because a course issues two kinds of sheet and each has its own builder and its own
set of documents: a handout is printed three ways and a homework sheet two.
"""
from core.builder.products import Node, Product

#: `modules/scholar/builder/handout.py`.
HANDOUT = Node('handout', (
    Product('handout-students', 'handout-students.jtex'),
    Product('handout-solutions', 'handout-solutions.jtex'),
    Product('handout-solved', 'handout-solved.jtex'),
))

#: `modules/scholar/builder/homework.py`.
HOMEWORK = Node('homework', (
    Product('homework-students', 'homework-students.jtex'),
    Product('homework-solutions', 'homework-solutions.jtex'),
))

#: Keyed by the directory the issues sit in, which is what the graph walks and what
#: `HandoutMixin._subdir` / `HomeworkMixin._subdir` already say on the context side. The builder
#: module's name is the key the graph passes to `python -m modules.scholar.builder.<builder>`.
NODES = {'handouts': HANDOUT, 'homework': HOMEWORK}
BUILDERS = {'handouts': 'handout', 'homework': 'homework'}
