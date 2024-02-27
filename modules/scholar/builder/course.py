from modules.scholar.builder.builder import BuilderCourseBase
from modules.scholar.builder.contexts.hierarchy import ContextCourse


class BuilderCourse(BuilderCourseBase):
    _target = 'course'
    _root_context_class = ContextCourse

    templates = [
        'course.tex',
    ]

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('course', type=str)

    def ident(self):
        return (self.args.course,)


BuilderCourse().build_templates()
