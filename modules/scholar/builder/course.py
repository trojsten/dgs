import builder
import context


class BuilderCourse(builder.BuilderCourseBase):
    _target = 'course'
    _root_context_class = context.ContextCourse

    templates = [
        'course.tex',
    ]

    def create_argument_parser(self):
        super().create_argument_parser()
        self.parser.add_argument('course', type=str)

    def id(self):
        return self.args.course,


BuilderCourse().build()
