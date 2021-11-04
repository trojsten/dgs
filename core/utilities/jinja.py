import jinja2
import os
import sys

from core.utilities import dicts, filters, colour as c


# Create a custom LaTeX Jinja2 environment, including filters
def environment(directory):
    env = jinja2.Environment(
        block_start_string='(@',
        block_end_string='@)',
        variable_start_string='(*',
        variable_end_string='*)',
        comment_start_string='(#',
        comment_end_string='#)',
        line_statement_prefix='%%',
        line_comment_prefix='%#',
        trim_blocks=True,
        autoescape=False,
        undefined=jinja2.StrictUndefined,
        loader=jinja2.FileSystemLoader(directory),
    )

    dicts.merge(env.filters, {
        'roman': filters.roman,
        'format_list': filters.format_list,
        'isotex': filters.isotex,
    })

    dicts.merge(env.globals, {
        'checkdigit': check_digit,
        'plural': plural,
    })

    return env


# Compute a barcode128 check digit
def check_digit(venue, team, problem):
    digits = list(map(int, list('{:03d}{:03d}{:02d}0'.format(venue, team, problem))))
    raw = sum([x * y for x, y in zip(digits, [3, 7, 1, 3, 7, 1, 3, 7, 1])])
    return 9 - (raw - 1) % 10

def plural(how_many, one, two, default):
    if how_many == 1:
        return one
    if how_many > 2 and how_many < 5:
        return two
    else:
        return default

# Print a Jinja2 template with provided context
def print_template(root, template, context, output_directory=None, new_name=None):
    template_path = f'{root}/{template}'
    output_path = sys.stdout if output_directory is None else open(os.path.join(output_directory, template if new_name is None else new_name), 'w')
    try:
        print(f"Rendering template {c.path(template_path)} to {c.path(output_path.name)}")
        print(
            environment(root).get_template(template).render(context),
            file=output_path,
        )
    except jinja2.exceptions.TemplateNotFound as e:
        print(f"{c.err('Template not found')}: {c.path(template_path)}, {c.err('aborting')}")
