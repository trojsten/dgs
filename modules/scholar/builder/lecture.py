import builder
import context


class BuilderLecture(builder.BuilderCourseBase):
    target = 'lecture'
    root_context_class = context.ContextScholarLecture

    templates = [
        'lecture.tex',
    ]

    def add_arguments(self):
        super().add_arguments()
        self.parser.add_argument('course', type=str)
        self.parser.add_argument('lecture', type=str)

    def id(self):
        return (self.args.course, self.args.lecture)


BuilderLecture().build()
