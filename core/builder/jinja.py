import functools
import math
import os
from abc import abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any

import jinja2
import numpy as np
import pint

from core.builder.context.quantities import PhysicsQuantity, QuantityList, QuantityProduct, QuantityRange
from core.filters import latex, numbers
from core.utilities import colour as c
from core.utilities import logger

log = logger.setupLog('dgs')

ureg = pint.UnitRegistry(preprocessors=[lambda s: s.replace("€", "EUR")])
ureg.define("eur = [currency] = € = EUR")
pint.set_application_registry(ureg)


class MissingVariablesError(Exception):
    def __init__(self, missing, *, template):
        super().__init__(f"Missing variables in {c.path(template)}: {missing}")
        self.missing = missing


def make_collect_undefined():
    """
    Factory so each Environment gets its own fresh registry.

    Collection happens lazily: we record a missing name only when the
    undefined is *actually used* in a way that would normally produce
    output or raise (rendering, arithmetic, attribute access, etc.).
    This means the `default` filter can intercept the undefined and
    substitute a fallback without the name being counted as a real miss.
    """
    collected = []

    class CollectUndefined(jinja2.Undefined):
        __slots__ = ()  # jinja2.Undefined uses __slots__; mirror that

        def _record(self):
            if self._undefined_name is not None:
                collected.append(self._undefined_name)

        # Catches arithmetic, attribute access on non-dunder names, calls, etc.
        def _fail_with_undefined_error(self, *args, **kwargs):
            self._record()
            return ''

        # Bare `(* missing *)` interpolation goes through __str__ on the
        # base Undefined, which silently returns ''. Override to record.
        def __str__(self):
            self._record()
            return ''

    CollectUndefined._collected = collected
    return CollectUndefined


class JinjaRenderer:
    """
    A wrapper class for rendering Jinja2 templates.
    Supports custom tag delimiters and emits strict warnings everywhere.
    """
    def __init__(self,
                 *,
                 loader: jinja2.BaseLoader = jinja2.BaseLoader(),
                 **kwargs):
        self._undefined_cls = make_collect_undefined()
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
            undefined=self._undefined_cls,
            loader=loader,
            **kwargs,
        )

    def render(self,
               template: str | Path,
               context: dict[str, Any]) -> str:
        """ Render in memory """
        self._undefined_cls._collected.clear()
        output = self._render(template, context=context)

        if missing := list(dict.fromkeys(self._undefined_cls._collected)):
            raise MissingVariablesError(missing, template=template)

        return output


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
            raise
        except jinja2.exceptions.TemplateSyntaxError as e:
            log.critical(f"Template syntax error in {c.path(template.name)}: {c.err(e)}")
            raise
        # Other exceptions are deferred to the base class


class MarkdownJinjaRenderer(JinjaRenderer):
    """
    A Jinja2 renderer for pre-rendering dynamically added Markdown files.

    String-based, expects the whole template to be provided as a string.
    Includes mathematical functions, basic constants, and numerous formatting filters.
    """
    @staticmethod
    def __generate_format_functions(func: Callable[[Any], Callable], tag: str):
        """
        Generate formatting function shorthands for a particular format and all precisions between 0 and 9.
        """
        return {f'{tag}{prec:d}': functools.partial(func, precision=prec) for prec in range(10)}

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
            'n': latex.num,
            'nf': latex.num_float,
            'ng': latex.num_general,
            'ef': latex.equals_float,
            'eg': latex.equals_general,
            'af': latex.approx_float,
            'ag': latex.approx_general,
            'w': lambda obj, value: obj.widen(value),      # This is so that we can call it on both Quantity and Range
            'widen': lambda obj, value: obj.widen(value),
            'mag': lambda q: q.mag,
            'unit': PhysicsQuantity.only_unit,
            'sim': PhysicsQuantity.simplify,
        } |
        self.__generate_format_functions(numbers.format_float, 'f') |
        self.__generate_format_functions(numbers.format_general, 'g') |
        self.__generate_format_functions(latex.num_float, 'nf') |
        self.__generate_format_functions(latex.num_general, 'ng') |
        self.__generate_format_functions(latex.equals_float, 'ef') |
        self.__generate_format_functions(latex.equals_general, 'eg') |
        self.__generate_format_functions(latex.approx_float, 'af') |
        self.__generate_format_functions(latex.approx_general, 'ag') | {
           'inline': latex.math_inline,
           'disp': latex.math_display,                                  # full function
           'dispd': functools.partial(latex.math_display, punct='.'),   # shorthand with dot
           'dispc': functools.partial(latex.math_display, punct=','),   # shorthand with comma
           'disps': functools.partial(latex.math_display, punct=';'),   # shorthand with semicolon
           'dispq': functools.partial(latex.math_display, punct='?'),   # shorthand with question mark
           'dispe': functools.partial(latex.math_display, punct='!'),   # shorthand with exclamation mark
           'align': latex.math_aligned,                                 # full function
           'alignd': functools.partial(latex.math_aligned, punct='.'),  # shorthand with dot
           'alignc': functools.partial(latex.math_aligned, punct=','),  # shorthand with comma
           'aligns': functools.partial(latex.math_aligned, punct=';'),  # shorthand with semicolon
           'alignq': functools.partial(latex.math_aligned, punct='?'),  # shorthand with question mark
           'aligne': functools.partial(latex.math_aligned, punct='!'),  # shorthand with exclamation mark
        })

        self.env.globals |= {
            'Q': PhysicsQuantity.construct,
            'QuantityList': QuantityList,
            'QL': QuantityList,
            'QuantityProduct': QuantityProduct,
            'QP': QuantityProduct,
            'QuantityRange': QuantityRange,
            'QR': QuantityRange,
        } | {
            'sin': np.sin,
            'cos': np.cos,
            'tan': np.tan,
            'asin': np.asin,
            'acos': np.acos,
            'atan': np.atan,
            'atan2': np.atan2,
            'ceil': lambda x: PhysicsQuantity.ceil(x) if isinstance(x, PhysicsQuantity) else np.ceil(x),
            'floor': lambda x: PhysicsQuantity.floor(x) if isinstance(x, PhysicsQuantity) else np.floor(x),
            'sqrt': lambda x: (x ** 0.5),
            'cbrt': np.cbrt,
            'rad': np.radians,
            'deg': np.degrees,
            'gamma': math.gamma,
            'beta': lambda x, y: math.gamma(x) * math.gamma(y) / math.gamma(x + y),
            'log': np.log,
            'log10': np.log10,
            'log2': np.log2,
            'exp': np.exp,
            'pow': np.power,
            'pi': np.pi,
            'tau': math.tau,
            'euler': math.e,
        }

    def _render(self,
                template: str,
                context: dict[str, Any]):
        return self.env.from_string(template).render(**context)
