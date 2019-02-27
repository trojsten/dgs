import os
import base

import core.utilities.colour as c

class BuilderNabojVenue(base.BuilderNaboj):
    target = 'venue'

    def __init__(self):
        self.rootContextClass = base.ContextTearoff
        self.templates = {
            'templates':    ['barcodes.txt', 'tearoff.tex', 'envelope.tex'],
        }
        super().__init__()

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
