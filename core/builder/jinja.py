import jinja2
import os
import sys
import logging
from pathlib import Path

from typing import Any, Optional

from core.utilities import filters, colour as c

log = logging.getLogger('dgs')


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


class Renderer:
    def __init__(self, template_root):
        self.template_root = template_root

        self.env = jinja2.Environment(
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
            undefined=CollectUndefined,
            loader=jinja2.FileSystemLoader(self.template_root),
        )

        self.env.filters |= {
            'roman': filters.roman,
            'format_list': filters.render_list,
            'format_people': filters.format_people,
            'format_gender_suffix': filters.format_gender_suffix,
            'isotex': filters.isotex,
            'plural': filters.plural,
            'nth': filters.nth,
            'upnth': filters.upnth,
        }

        self.env.globals |= {
            'checkdigit': filters.check_digit,
            'plural': filters.plural,
            'textbf': filters.textbf,
            'path_exists': lambda x: os.path.exists(x),
        }


    def render(self,
               template: Path,
               context: dict[str, Any],
               *,
               outfile: Optional[Path] = None):
        template_path = self.template_root / template

        if outfile is None:
            output_path = sys.stdout
        else:
            output_path = outfile

        try:
            log.info(f"Rendering template {c.path(template_path)} to {c.path(output_path.name)}")
            print(
                self.env.get_template(template).render(context),
                file=output_path,
            )
        except jinja2.exceptions.TemplateNotFound as e:
            log.critical(f"{c.err('Template not found')}: {c.path(template_path)}, {c.err('aborting')}")
            raise e
        except jinja2.exceptions.UndefinedError as e:
            log.critical(f"Missing required variable from context in {c.path(template)}: {c.err(e)}")
            raise e
