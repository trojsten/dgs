from pathlib import Path

from core import i18n
from core.builder.jinja import Renderer
from core.builder.context import Context


class StandaloneRenderer:
    template = 'standalone.jtt'

    def __init__(self, locale_code: str, infile, outfile, **options):
        self.locale_code: str = locale_code
        self.locale: i18n.Locale = i18n.languages[locale_code]
        self.infile = infile
        self.outfile = outfile
        self.template_root = Path('core/templates/')

        content = '    '.join(infile.readlines())
        self.context = Context(content=content)

        self.jinja = Renderer(self.template_root)

    def run(self):
        self.jinja.render(self.template, self.context.data, outfile=self.outfile)
        return 0
