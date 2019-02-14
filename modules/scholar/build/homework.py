import os
import base

class BuilderHomework(base.BuilderScholar):
    def __init__(self):
        super().__init__(
            base.ContextHomework,
            formatters      = ['format-homework.tex'],
            templates       = ['homework.tex'],
            templateRoot    = os.path.dirname(os.path.dirname(__file__)),
        )
        self.target = 'homework'

builder = BuilderHomework()
