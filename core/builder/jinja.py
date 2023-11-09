import jinja2
import os
import sys
import itertools
import logging
from pathlib import Path

from core.utilities import dicts, filters, colour as c, logger

logger = logger.setupLog('root')


class CollectUndefined(jinja2.StrictUndefined):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.missing = []

    def __call__(self, *args, **kwargs):
        undefined = self.undefined_cls(*args, **kwargs)
        self.missing.append(undefined._undefined_name)
        return undefined

    def assert_no_missing(self):
        if len(self.missing) > 0:
            raise MissingVariablesError(self.missing)


class MissingVariablesError(Exception):
    def __init__(self, missing, *args):
        super().__init__(*args)
        self.missing = missing

    def __str__(self):
        return f"Missing variables: {self.missing}"


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

    env.filters |= {
        'roman': filters.roman,
        'format_list': filters.render_list,
        'format_people': filters.format_people,
        'format_gender_suffix': filters.format_gender_suffix,
        'isotex': filters.isotex,
        'plural': filters.plural,
        'nth': filters.nth,
        'upnth': filters.upnth,
    }

    env.globals |= {
        'checkdigit': filters.check_digit,
        'plural': filters.plural,
        'textbf': filters.textbf,
    }

    return env


def print_template(root, template, context, *, outdir=None, new_name=None):
    """ Print a Jinja2 template with provided context """
    template_path = Path(root, template)
    if outdir is None:
        output_path = sys.stdout
    else:
        output_path = open(Path(outdir, template if new_name is None else new_name), 'w')
    try:
        logger.info(f"Rendering template {c.path(template_path)} to {c.path(output_path.name)}")
        print(
            environment(root).get_template(template).render(context),
            file=output_path,
        )
    except jinja2.exceptions.TemplateNotFound as e:
        logger.critical(f"{c.err('Template not found')}: {c.path(template_path)}, {c.err('aborting')}")
        raise e
    except jinja2.exceptions.UndefinedError as e:
        logger.critical(f"Missing required variable from context in {c.path(template)}: {c.err(e)}")
        raise e
