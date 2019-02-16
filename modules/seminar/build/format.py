import os
import base

class BuilderFormat(base.BuilderSeminar):
    def __init__(self):
        self.rootContextClass = base.ContextBooklet
        super().__init__()
        self.target = 'handout'

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
        self.templates = {
            'format': ['{}.tex'.format(self.target)],
        }

BuilderFormat().build()
