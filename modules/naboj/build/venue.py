import os
import base

import core.utilities.colour as c

class BuilderNabojVenue(base.BuilderNaboj):
    def __init__(self):
        self.templates          = {
            'templates':    ['barcodes.txt', 'tearoff.tex', 'envelope.tex'],
        }
        self.target = 'venue'
        self.rootContextClass = base.ContextTearoff
        super().__init__()
        self.context = self.rootContextClass(os.path.realpath(self.args.launch), self.args.competition, self.args.volume, self.args.venue)

    def createArgParser(self):
        super().createArgParser()
        self.parser.add_argument('-p', '--venue', type = str)

    def printBuildInfo(self):
        print(c.act("Invoking Náboj template builder on"), c.name(self.target),
            c.path("{competition}/{volume}/{venue}".format(
                competition = self.args.competition,
                volume      = self.args.volume,
                venue       = self.args.venue,
            ))
        )

BuilderNabojVenue().build()
