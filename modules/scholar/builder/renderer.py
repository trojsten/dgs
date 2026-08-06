#!/usr/bin/env python
import datetime
import logging
from pathlib import Path

from enschema import Optional, Schema

from core.builder import renderer

log = logging.getLogger('dgs')

#: A handout is dated; homework is due. Both are required -- every one of the 41 handouts carries
#: a `date` and every one of the 26 homework sheets a `deadline`, and a sheet missing its own is
#: a mistake worth being told about rather than a shape to tolerate.
SHEET_SCHEMAS = {
    'handouts': Schema({
        'date': datetime.date,
        Optional('title'): str,
    }),
    'homework': Schema({
        'deadline': datetime.date,
    }),
}

#: A problem carries at most a heading and a flag. `title` and `name` both appear -- 25 and 26
#: times across the tree -- and neither is going away without a pass over the sources, so both
#: are accepted here rather than one being declared wrong by fiat.
PROBLEM_SCHEMA = Schema({
    Optional('title'): str,
    Optional('name'): str,
    Optional('bonus'): bool,
})


def schema_for(path: Path) -> Schema:
    """
    Which front matter this file may carry, from where it sits.

    `<course>/<year>/<kind>/<issue>/meta.yaml` is a sheet and `<...>/<issue>/<problem>/meta.yaml`
    is a problem inside one, and the two want different things -- so a single schema for all of
    scholar could only ever be the union of both, which is what it used to be, and which let a
    handout go undated.
    """
    parts = path.parts
    for kind, schema in SHEET_SCHEMAS.items():
        if kind in parts:
            is_sheet = len(parts) - parts.index(kind) == 3      # <kind>/<issue>/meta.yaml
            return schema if is_sheet else PROBLEM_SCHEMA
    return PROBLEM_SCHEMA


class ScholarStandaloneContext(renderer.StandaloneContext):
    """
    Scholar's front matter, which differs by what the file describes.

    The schema is chosen per instance rather than fixed on the class, because scholar is the one
    module where two different kinds of thing are rendered by the same command.
    """
    def __init__(self, new_id, path, **defaults):
        self._schema = renderer.StandaloneContext._schema | schema_for(Path(path))
        super().__init__(new_id, path, **defaults)


class CLIInterface(renderer.CLIInterface):
    """
    Jinja CLI interface
    """
    description = "dgs Jinja scholar convertor"
    context_cls = ScholarStandaloneContext


if __name__ == "__main__":
    CLIInterface().run()
