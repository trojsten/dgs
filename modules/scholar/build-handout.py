#!/usr/bin/env python3

from build import base

base.buildIssue(
    'handout',
    base.ContextHandout,
    ['format-handout.tex'],
    ['handout.tex'],
)
