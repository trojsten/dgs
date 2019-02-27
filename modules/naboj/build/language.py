import os
import base

import core.utilities.colour as c
import core.utilities.jinja as jinja

class BuilderNabojLanguage(base.BuilderNaboj):
    target = 'language'

    def __init__(self):
        self.rootContextClass = base.ContextBooklet
        self.templates          = {
            'format':       ['format-language.tex'],
            'templates':    ['booklet.tex', 'answers.tex', 'answers-mod5.tex', 'constants.tex', 'cover.tex', 'instructions.tex'],
        }
        super().__init__()
    
    def createArgParser(self):
        super().createArgParser()
        self.parser.add_argument('-l', '--language', type = str)

    def id(self):
        return (self.args.competition, self.args.volume, self.args.language)


    def build(self):
        super().build()
        for template in ['intro.tex', 'instructions-text.tex']:
            jinja.printTemplate(
                os.path.join(self.launchDirectory, self.args.competition, '{:02d}'.format(self.args.volume), 'languages', self.args.language),
                template, self.context.data, self.outputDirectory
            )

BuilderNabojLanguage().build()
