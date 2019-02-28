import jinja2, os, sys

import core.utilities.filters as filters
import core.utilities.dicts as dicts

# Create a custom LaTeX Jinja2 environment, including filters
def environment(directory):
    env = jinja2.Environment(
        block_start_string = '(@',
        block_end_string = '@)',
        variable_start_string = '(*',
        variable_end_string = '*)',
        comment_start_string = '\#{',
        comment_end_string = '}',
        line_statement_prefix = '%%',
        line_comment_prefix = '%#',
        trim_blocks = True,
        autoescape = False,
        undefined = jinja2.StrictUndefined,
        loader = jinja2.FileSystemLoader(directory),
    )

    dicts.merge(env.filters, {
        'roman':        filters.roman,
        'formatList':   filters.formatList,
        'isotex':       filters.isotex,
    })

    dicts.merge(env.globals, {
        'checkdigit':   checkdigit,
    })

    return env

def checkdigit(venue, team, problem):
    digits = list(map(int, list('{:03d}{:03d}{:02d}0'.format(venue, team, problem))))
    raw = sum([x*y for x, y in zip(digits, [3, 7, 1, 3, 7, 1, 3, 7, 1])])
    return 9 - (raw - 1) % 10

# Print a Jinja2 template with provided context
def printTemplate(templateRoot, template, context, outputDirectory = None, newName = None):
    print(
        environment(templateRoot).get_template(template).render(context),
        file = sys.stdout if outputDirectory is None else open(os.path.join(outputDirectory, template if newName is None else newName), 'w')
    )
