import builder
import context


class BuilderFormat(builder.BuilderSeminar):
    root_context_class = context.ContextBooklet
    target = 'format'

    def parse_arguments(self):
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
            'format': [f'format-{self.target}.tex'],
        }


BuilderFormat().build()
