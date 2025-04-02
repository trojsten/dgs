from pathlib import Path

from core import i18n
from core.builder.jinja import Renderer
from core.builder.context import Context


class TikzRenderer:
    def __init__(self, locale_code: str, infile, outfile, **options):
        self.locale_code: str = locale_code
        self.locale: i18n.Locale = i18n.languages[locale_code]
        self.infile = infile
        self.outfile = outfile
        self.file = None
        self.template_root = Path('')

        self.context = Context(tikzfile=infile)

        self.jinja = Renderer(self.template_root)

    def run(self):
        self.jinja.render(self.template_root, 'core/latex/tikz.jtt', self.context.data)
        return 0
