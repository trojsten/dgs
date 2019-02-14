#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys, pprint, colorama

class BuilderRound(base.BuilderScholar):
    def __init__(self):
        super().__init__(
            base.ContextHandout,
            formatters      = ['format-handout.tex'],
            templates       = ['problems.tex', 'solutions.tex'],
            templateRoot    = os.path.dirname(os.path.dirname(__file__)),
        )
        self.target = 'handout'

builder = BuilderRound()

context = build.ContextBooklet(launchDirectory, args.competition, args.volume, args.semester, args.round)
