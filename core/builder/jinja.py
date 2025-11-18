import functools
import math
from abc import abstractmethod
from pathlib import Path

import jinja2
import os
import numpy as np

from typing import Any

from core.builder.context.quantities import PhysicsQuantity, QuantityRange
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
    """ Jinja error emitted when variables used in the template are missing from the context. """
    def __init__(self, missing, *args):
        super().__init__(*args)
        self.missing = missing

    def __str__(self):
        return f"Missing variables: {self.missing}"


class JinjaRenderer:
    """
    A wrapper class for rendering Jinja2 templates.
    Supports custom tag delimiters and emits strict warnings everywhere.
    """
    def __init__(self,
                 *,
                 loader: jinja2.BaseLoader = jinja2.BaseLoader(),
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
            loader=loader,
            **kwargs,
        )

    def render(self,
               template: str | Path,
               context: dict[str, Any]) -> str:
        """
        Render in memory
        """
        try:
            return self._render(template, context=context)
        except jinja2.exceptions.UndefinedError as e:
            log.critical(f"Missing required variable from context: {c.err(e)}")
            raise e
        except jinja2.exceptions.TemplateSyntaxError as e:
            log.critical(f"Template syntax error: {e}")
            raise e

    @abstractmethod
    def _render(self,
                template: Any,
                context: dict[str, Any]) -> str:
        """
        Inner render method, to be overridden by subclasses if necessary.
        """


class StaticRenderer(JinjaRenderer):
    """
    A Jinja2 renderer for pre-rendering static TeX content from the modules.
    Includes ad hoc utility functions.
    """
    def __init__(self, template_root: os.PathLike, **kwargs: object) -> None:
        super().__init__(loader=jinja2.FileSystemLoader(template_root), **kwargs)
        self.template_root = template_root

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
            'path_exists': os.path.exists,
            'file_size': os.path.getsize,
        }

    def _render(self,
                template: Path,
                context: dict[str, Any]) -> str:
        """
        Render the template to a string, catching and logging most typical exceptions

        # ToDo: find if there are more worth of any attention
        """
        log.debug(f"Rendering {template}")

        try:
            return self.env.get_template(template.name).render(**context)
        except jinja2.exceptions.UndefinedError as e:
            log.critical(f"Missing required variable from context in {c.path(template.name)}: {c.err(e)}")
            raise e
        except jinja2.exceptions.UndefinedError as e:
            log.critical(f"Missing required variable from context in {c.path(template.name)}: {c.err(e)}")
            raise e
        except jinja2.exceptions.TemplateSyntaxError as e:
            log.critical(f"Template syntax error in {c.path(template.name)}: {c.err(e)}")
            raise e
        # Other exceptions are deferred to the base class


class MarkdownJinjaRenderer(JinjaRenderer):
    """
    A Jinja2 renderer for pre-rendering dynamically added Markdown files.

    String-based, expects the whole template to be provided as a string.
    Includes mathematical functions, basic constants, and numerous formatting filters.
    """
    @staticmethod
    def __generate_format_functions(func, tag):
        """
        Generate formatting function shorthands for a particular format and all precisions between 0 and 9.
        """
        return {f'{tag}{prec:d}': functools.partial(func, precision=prec) for prec in range(0, 10)}

    def __init__(self, **kwargs):
        """
        Markdown renderer overrides variable tags to `(§ §)` so as not to clash with Markdown syntax.
        """
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
            'w': QuantityRange.widen,
            'widen': QuantityRange.widen,
        } |
        self.__generate_format_functions(numbers.format_float, 'f') |
        self.__generate_format_functions(numbers.format_general, 'g') |
        self.__generate_format_functions(latex.num_float, 'nf') |
        self.__generate_format_functions(latex.num_general, 'ng') |
        self.__generate_format_functions(latex.equals_float, 'ef') |
        self.__generate_format_functions(latex.equals_general, 'eg')) | {
            'inline': latex.math_inline,
            'disp': latex.math_display,
            'align': latex.math_aligned,
        }

        self.env.globals |= {
            'Q': PhysicsQuantity.construct,
        } | {
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
        } | {
            'KtoC': lambda x: x - 273.15,
            'CtoK': lambda x: x + 273.15,
        }

    def _render(self,
                template: str,
                context: dict[str, Any]):
        return self.env.from_string(template).render(**context)
