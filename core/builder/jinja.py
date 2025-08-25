import functools
import math
from pathlib import Path

import jinja2
import os
import sys
import numpy as np

from typing import Any, Optional, TextIO

from core.builder.context.quantity import PhysicsQuantity
from core.utilities import colour as c, logger
from core.filters import latex, numbers

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
    """
    A wrapper class for rendering Jinja2 templates.
    Supports custom tag delimiters
    """
    def __init__(self,
                 **kwargs):
        self.env = jinja2.Environment(
            block_start_string=kwargs.pop('block_start_string', '(@'),
            block_end_string=kwargs.pop('block_end_string', '@)'),
            variable_start_string=kwargs.pop('variable_start_string', '(*'),
            variable_end_string=kwargs.pop('variable_end_string', '*)'),
            comment_start_string=kwargs.pop('comment_start_string', '(#'),
            comment_end_string=kwargs.pop('comment_end_string', '#)'),
            line_statement_prefix=kwargs.pop('line_statement_prefix', '@J'),
            line_comment_prefix=kwargs.pop('line_comment_prefix', '%#'),
            trim_blocks=True,
            autoescape=False,
            undefined=CollectUndefined,
            loader=jinja2.DictLoader({'template': kwargs.pop('template', '')}),
            **kwargs
        )

    @staticmethod
    def __default_to_stdout(outfile: Optional[TextIO]):
        if outfile is None:
            return sys.stdout
        else:
            return outfile

    def render_in_memory(self,
                         context: dict[str, Any],
                         *,
                         outfile: Optional[TextIO] = None) -> str:
        """
        Render in memory
        """
        output_path = self.__default_to_stdout(outfile)

        try:
            log.info(f"Rendering a template to {c.path(output_path.name)}")
            return self.env.get_template('template').render(**context)
        except jinja2.exceptions.UndefinedError as e:
            log.critical(f"Missing required variable from context: {c.err(e)}")
            raise e

    def render(self,
               template: Path,
               context: dict[str, Any],
               *,
               outfile: Optional[TextIO] = None):
        template_path = self.template_root / template
        output_path = self.__default_to_stdout(outfile)

        try:
            log.info(f"Rendering template {c.path(template_path)} to {c.path(output_path.name)}")
            print(
                self.env.get_template(template.name).render(context),
                file=output_path,
            )
        except jinja2.exceptions.TemplateNotFound as e:
            log.critical(f"{c.err('Template not found')}: {c.path(template_path)}, {c.err('aborting')}")
            raise e
        except jinja2.exceptions.UndefinedError as e:
            log.critical(f"Missing required variable from context in {c.path(template)}: {c.err(e)}")
            raise e


class StaticRenderer(JinjaRenderer):
    """
    A Jinja2 renderer for pre-rendering static TeX content from the modules.
    Includes ad hoc utility functions.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.env.filters |= {
            'roman': numbers.roman,
            'format_list': latex.render_list,
            'format_people': latex.format_people,
            'format_gender_suffix': latex.format_gender_suffix,
            'isotex': latex.isotex,
            'plural': numbers.plural,
            'nth': numbers.nth,
            'upnth': latex.upnth,
        }

        self.env.globals |= {
            'plural': numbers.plural,
            'textbf': latex.textbf,
            'path_exists': lambda x: os.path.exists(x),
        }


def construct_unit(magnitude, unit, *, symbol: Optional[str] = None):
    return PhysicsQuantity.construct(magnitude, unit, symbol=symbol)


class MarkdownJinjaRenderer(JinjaRenderer):
    """
    A Jinja2 renderer for pre-rendering dynamic Markdown files.
    Includes mathematical functions, basic constants, and number formatting filters.
    """
    @staticmethod
    def __generate_functions(func, tag):
        return {f'{tag}{prec:d}': functools.partial(func, precision=prec) for prec in range(0, 10)}

    def __init__(self, **kwargs):
        super().__init__(variable_start_string='(§',
                         variable_end_string='§)',
                         **kwargs)

        self.env.filters |= ({
            'f': numbers.format_float,
            'g': numbers.format_general,
            'nf': latex.num_float,
            'ng': latex.num_general,
            'ef': latex.equals_float,
            'eg': latex.equals_general,
        } |
        self.__generate_functions(numbers.format_float, 'f') |
        self.__generate_functions(numbers.format_general, 'g') |
        self.__generate_functions(latex.num_float, 'nf') |
        self.__generate_functions(latex.num_general, 'ng') |
        self.__generate_functions(latex.equals_float, 'ef') |
        self.__generate_functions(latex.equals_general, 'eg'))

        self.env.globals |= {
            'u': construct_unit,
            'sin': np.sin,
            'cos': np.cos,
            'tan': np.tan,
            'asin': np.asin,
            'acos': np.acos,
            'atan': np.atan,
            'atan2': np.atan2,
            'ceil': np.ceil,
            'floor': np.floor,
            'sqrt': lambda x: (x ** 0.5),
            'cbrt': np.cbrt,
            'rad': np.radians,
            'deg': np.degrees,
            'gamma': math.gamma,
            'log': np.log,
            'log10': np.log10,
            'log2': np.log2,
            'exp': np.exp,
            'pow': np.pow,
            'pi': np.pi,
            'tau': math.tau,
            'euler': math.e,
            'KtoC': lambda x: x - 273.15,
            'CtoK': lambda x: x + 273.15,
        }
