from pathlib import Path
from typing import TextIO, Optional

from core import i18n
from core.builder.jinja import StaticRenderer, JinjaRenderer
from core.builder.context import Context


class BuilderStandalone:
    template = 'standalone.jtex'

    def __init__(self,
                 locale_code: str,
                 infile: TextIO,
                 outfile: Optional[TextIO] = None,
                 **options):
        self.locale_code: str = locale_code
        self.locale: i18n.Locale = i18n.languages[locale_code]
        self.infile = infile
        self.outfile = outfile
        self.template_root = Path('core/templates/')

        content = '    '.join(infile.readlines())
        self.context = Context(content=content, lang=self.locale_code)
        self.renderer = StaticRenderer(self.template_root)
        self.run()

    def run(self):
        print(
            self.renderer.render(Path(self.template), self.context.data),
            file=self.outfile,
        )
