import os
import base
import core.utilities.jinja as jinja
import core.utilities.colour as c

class BuilderFormat(base.BuilderSeminar):
    def __init__(self):
        super().__init__(
            base.ContextBooklet,
            templateRoot    = os.path.dirname(os.path.dirname(__file__)),
        )
    
    def parseArgs(self):
        args = self.parser.parse_args()

        if args.competition is None:
            self.target = 'root'
            args.volume = args.semester = args.round = None
        elif args.volume is None:
            self.target = 'competition'
            args.semester = args.round = None
        elif args.semester is None:
            self.target = 'volume'
            args.round = None
        elif args.round is None:
            self.target = 'semester'
        else:
            self.target = 'round'

        self.args = args
        self.formatters = ['format-{}.tex'.format(self.target)]

builder = BuilderFormat()
builder.debugInfo()
builder.build()
