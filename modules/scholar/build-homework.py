#!/usr/bin/env python3

from build import base

base.buildIssue(
    'homework',
    base.ContextHomework,
    ['format-homework.tex'],
    ['homework.tex'],
)
