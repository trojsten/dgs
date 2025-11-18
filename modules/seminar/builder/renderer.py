#!/usr/bin/env python
import logging

from abc import ABC

from enschema import Schema, And, Optional, Or
from schema import Literal

from core.builder import renderer

log = logging.getLogger('dgs')


class SeminarStandaloneContext(renderer.StandaloneContext):
    persons = Or(Schema(Literal('')),
                 Schema([{
                     'name': str,
                     'gender': Or(Literal('m'), Literal('f'), Literal('?')),
                 }]))
    _schema = renderer.StandaloneContext._schema | Schema({
        'title': And(str, len),
        'id': str,
        'evaluation': persons,
        'solution': persons,
        'points': {
            'description': And(int, lambda x: x >= 0),
            Optional('code'): And(int, lambda x: x >= 0),
            Optional('extra'): And(int, lambda x: x >= 0),
        },
    })


class CLIInterface(renderer.CLIInterface, ABC):
    """
    Jinja CLI interface
    """
    description = "dgs Jinja seminar convertor"
    context_cls = SeminarStandaloneContext


if __name__ == "__main__":
    CLIInterface().run()