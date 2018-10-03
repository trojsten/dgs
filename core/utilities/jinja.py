import jinja2, os, sys

import core.utilities.filters as filters
import core.utilities.context as context

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
        loader = jinja2.FileSystemLoader(directory),
    )

    context.mergeDicts(env.filters, {
        'roman':        filters.roman,
        'formatList':   filters.formatList,
    })

    return env

# Print a Jinja2 template with provided context
def printTemplate(templateRoot, template, context, outputDirectory = None):
    print(
        environment(templateRoot).get_template(template).render(context),
        file = sys.stdout if outputDirectory is None else open(os.path.join(outputDirectory, template), 'w')
    )

