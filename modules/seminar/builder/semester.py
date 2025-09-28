#!/usr/bin/env python3
import builder
import context


class BuilderSemester(builder.BuilderSemester):
    root_context_class = context.ContextSemesterBooklet
    templates = [
        'semester.jtex',
    ]
    target = 'semester'


BuilderSemester().build()
