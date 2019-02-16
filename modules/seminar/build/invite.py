import os
import base

class BuilderInvite(base.BuilderSeminar):
    def __init__(self):
        self.rootContextClass   = base.ContextInvite
        self.formatters         = []
        self.templates          = ['problems.tex', 'solutions.tex']
        super().__init__()
        self.target = 'invite'

BuilderRound().build()


print(Fore.CYAN + Style.DIM + "Invoking template builder on invite '{competition}/{volume}/{semester}'".format(
    competition = args.competition,
    volume      = args.volume,
    semester    = args.semester,
) + Style.RESET_ALL)

for template in ['invite.tex']:
    print(jinjaEnv(os.path.join(thisDirectory, 'templates')).get_template(template).render(context),
        file = open(os.path.join(outputDirectory, template), 'w') if outputDirectory else sys.stdout)

for template in ['intro.tex', 'rules.tex']:
    print(jinjaEnv(os.path.join(thisDirectory, 'styles', args.competition, 'templates')).get_template(template).render(context),
        file = open(os.path.join(outputDirectory, template), 'w') if outputDirectory else sys.stdout)

print(Fore.GREEN + "Template builder successful" + Style.RESET_ALL)

