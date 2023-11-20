#!/usr/bin/env python3
import builder
import context


class BuilderRound(builder.BuilderRound):
    root_context_class = context.ContextBooklet
    templates = [
        'problems.jtt',
        'solutions.jtt',
        'solutions-full.jtt',
        'instagram.jtt',
    ]
    target = 'round'


BuilderRound().build()
