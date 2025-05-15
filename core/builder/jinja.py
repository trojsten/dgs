import math
import jinja2
import os
import sys

from typing import Any, Optional, TextIO

import core
from core.utilities import filters, colour as c, logger

log = logger.setupLog('dgs')


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


class JinjaRenderer:
    def __init__(self,
                 template_root,
                 **kwargs):
        self.template_root = template_root

        self.env = jinja2.Environment(
            block_start_string=kwargs.pop('block_start_string', '(@'),
            block_end_string=kwargs.pop('block_end_string', '@)'),
            variable_start_string=kwargs.pop('variable_start_string', '(*'),
            variable_end_string=kwargs.pop('variable_end_string', '*)'),
            comment_start_string=kwargs.pop('comment_start_string', '(#'),
            comment_end_string=kwargs.pop('comment_end_string', '#)'),
            line_statement_prefix=kwargs.pop('line_statement_prefix', '%%'),
            line_comment_prefix=kwargs.pop('line_comment_prefix', '%#'),
            trim_blocks=True,
            autoescape=False,
            undefined=CollectUndefined,
            loader=jinja2.FileSystemLoader(self.template_root),
            **kwargs
        )

    def render(self,
               template: str,
               context: dict[str, Any],
               *,
               outfile: Optional[TextIO] = None):
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


class StaticRenderer(JinjaRenderer):
    def __init__(self, template_root, **kwargs):
        super().__init__(template_root, **kwargs)

        self.env.filters |= {
            'roman': core.utilities.filters.roman,
            'format_list': core.utilities.filters.render_list,
            'format_people': core.utilities.filters.format_people,
            'format_gender_suffix': core.utilities.filters.format_gender_suffix,
            'isotex': core.utilities.filters.isotex,
            'plural': core.utilities.filters.plural,
            'nth': core.utilities.filters.nth,
            'upnth': core.utilities.filters.upnth,
        }

        self.env.globals |= {
            'plural': core.utilities.filters.plural,
            'textbf': core.utilities.filters.textbf,
            'path_exists': lambda x: os.path.exists(x),
        }


class MarkdownJinjaRenderer(JinjaRenderer):
    def __init__(self, template_root, **kwargs):
        super().__init__(template_root, variable_start_string='(§', variable_end_string='§)', **kwargs)

        self.env.filters |= {
            #'qty': core.utilities.filters.qty,
            'num': core.utilities.filters.num,
        }

        self.env.globals |= {
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'asin': math.asin,
            'acos': math.acos,
            'atan': math.atan,
            'atan2': math.atan2,
            'ceil': math.ceil,
            'floor': math.floor,
            'sqrt': math.sqrt,
            'cbrt': math.cbrt,
            'rad': math.radians,
            'deg': math.degrees,
            'gamma': math.gamma,
            'ln': math.log,
            'log': math.log,
            'log10': math.log10,
            'log2': math.log2,
            'exp': math.exp,
            'pow': math.pow,
            'ktoc': lambda x: x - 273.15,
            'ctok': lambda x: x + 273.15,
        }
