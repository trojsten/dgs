import os
import base

import core.utilities.colour as c
import core.utilities.jinja as jinja

class BuilderNabojLanguage(base.BuilderNaboj):
    def __init__(self):
        super().__init__()
        self.templates          = {
            'format':       ['base.tex'],
            'templates':    ['booklet.tex', 'answers.tex', 'answers-mod5.tex', 'constants.tex', 'cover.tex', 'instructions.tex'],
        }
        self.target = 'language'
        self.rootContextClass = base.ContextBooklet
        self.context = self.rootContextClass(os.path.realpath(self.args.launch), self.args.competition, self.args.volume, self.args.language)
    
    def createArgParser(self):
        super().createArgParser()
        self.parser.add_argument('-l', '--language', type = str)

    def printBuildInfo(self):
        print(c.act("Invoking Náboj template builder on"), c.name(self.target),
            c.path("{competition}/{volume}/{language}".format(
                competition = self.args.competition,
                volume      = self.args.volume,
                language    = self.args.language,
            ))
        )

    def build(self):
        super().build()
        for template in ['intro.tex', 'instructions-text.tex']:
            jinja.printTemplate(
                os.path.join(self.launchDirectory, self.args.competition, '{:02d}'.format(self.args.volume), 'languages', self.args.language), template, self.context.data, self.outputDirectory
            )

BuilderNabojLanguage().build()
