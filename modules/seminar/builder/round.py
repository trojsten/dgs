import logging
from typing import ClassVar

from core.builder.jinja import StaticRenderer
from modules.seminar.builder import builder, context

log = logging.getLogger('dgs')


class BuilderRound(builder.BuilderSeminar):
    _root_context_class = context.ContextBooklet
    _target = 'round'

    _renderer_class = StaticRenderer

    #: What a Markdown repository's round produces, which is every seminar repository today.
    markdown_templates: ClassVar[list[str]] = [
        'problems.jtex',
        'solutions.jtex',
        'solutions-full.jtex',
        'instagram.jtex',
    ]

    #: And what a Typst one produces. Fewer, deliberately: the prototype sets a round's problems
    #: and its solutions, and the two documents that are about distribution rather than about
    #: the physics -- the full solutions with their credits, and the instagram squares -- wait
    #: until the shape has stopped moving.
    typst_templates: ClassVar[list[str]] = [
        'problems.jtyp',
        'solutions.jtyp',
    ]

    @property
    def templates(self) -> list[str]:
        """
        Which documents this round has, which follows the markup its repository is written in.

        A repository is wholly one flavour or the other -- `format:` in the competition's meta
        says which -- so this is a choice between two lists rather than a merge of them. A
        `.jtex` rendered against a Typst round would look right and reach xelatex full of Typst
        maths.
        """
        flavour = self.context.data['competition'].get('format', 'markdown')
        return self.typst_templates if flavour == 'typst' else self.markdown_templates


BuilderRound().build_templates()
