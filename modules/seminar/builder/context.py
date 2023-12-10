import datetime

from pathlib import Path
from abc import ABCMeta
from enschema import Schema, Optional, Use, And, Or

from core.utilities.schema import valid_language
from core.builder.context import FileSystemContext, BuildableFileSystemContext, ContextModule
from validators import SeminarRoundValidator


class ContextSeminar(FileSystemContext, metaclass=ABCMeta):
    def ident(self, competition=None, volume=None, semester=None, issue=None, problem=None):
        return (
            self._default(competition),
            self._default(volume, lambda x: f'{x:02d}'),
            self._default(semester, str),
            self._default(issue, str),
            self._default(problem, lambda x: f'{x:02d}'),
        )

    def node_path(self, competition=None, volume=None, semester=None, issue=None, problem=None):
        return Path(self.root, *self.ident(competition, volume, semester, issue, problem))


class ContextCompetition(ContextSeminar):
    _schema = Schema({
        'id': And(str, len),
        'short': And(str, len),
        'full': Schema({
            'nominative': And(str, len),
            Optional('genitive'): And(str, len),
            Optional('locative'): And(str, len),
        }),
        'urls': Schema({
            'web': And(str, len),  # set this to valid URL
            'submit': And(str, len),  # and here too
        }),
        'language': valid_language,
        'categories': [[], [And(str, len)]],
        'founded': int,
        Optional('email'): str,
        Optional('hacks'): dict,
        'head': Schema({
            'name': Or(
                And(str, len),
                {
                    'name': And(str, len),
                    'surname': And(str, len)
                },
            ),
            'email': And(str, len),  # change this to email
            'phone': And(str, len),  # change this to phone regex
        }),
        'organisation': dict,
    })

    def populate(self, competition):
        self.load_meta(competition) \
            .add_id(competition)


class ContextVolume(ContextSeminar):
    _schema = Schema({
        'id': str,
        'number': int,
        Optional('categories'): [[], [str]],
    })

    def populate(self, competition, volume):
        self.load_meta(competition, volume) \
            .add_id(f'{volume:02d}') \
            .add_number(volume)


class ContextSemester(ContextSeminar):
    _schema = Schema({
        'id': And(str, len),
        'number': And(int, lambda x: x in [1, 2]),
        'neuter': Schema({'nominative': str, 'genitive': str}),
        'feminine': Schema({'nominative': str, 'genitive': str}),
    })

    def populate(self, competition, volume, semester):
        self._id = str(semester)
        self.load_meta(competition, volume, semester) \
            .add_id(self.id) \
            .add_number(semester)
        # Add fancy names for the semesters
        # Maybe this should be a Jinja filter...?
        self.add(
            neuter={
                'nominative': ['zimné', 'letné'][semester - 1],
                'genitive': ['zimného', 'letného'][semester - 1],
            },
            feminine={
                'nominative': ['zimná', 'letná'][semester - 1],
                'genitive': ['zimnej', 'letnej'][semester - 1],
            },
        )


class ContextSemesterFull(ContextSemester, BuildableFileSystemContext):
    def populate(self, competition, volume, semester):
        self.add_subdirs(ContextRoundFull, 'rounds', (self.root, competition, volume, semester))


class ContextRound(ContextSeminar):
    defaults = {
        'instagram': {
            'skin': 'orange',
            'text_colour': 'black',
        }
    }

    _schema = Schema({
        'deadline': datetime.date,
        Optional('instagram'): Schema({
            'skin': Use(str, lambda x: x in ['orange', 'grey']),
            'text_colour': str,
        }),
        'id': And(str, len),
        'number': int,
    })

    def populate(self, competition, volume, semester, issue):
        self.load_meta(competition, volume, semester, issue) \
            .add_id(str(issue)) \
            .add_number(issue)


class ContextProblem(ContextSeminar):
    persons = Or('',
                 [{
                     'name': str,
                     'gender': Or('f', 'm', '?'),
                 }])
    _schema = Schema({
        'title': And(str, len),
        'categories': list,
        'number': And(int, lambda x: 1 <= x <= 8),
        'id': str,
        'evaluation': persons,
        'solution': persons,
        'points': {
            'description': And(int, lambda x: x >= 0),
            Optional('code'): And(int, lambda x: x >= 0),
            Optional('extra'): And(int, lambda x: x >= 0),
        },
    })

    def populate(self, competition, volume, semester, issue, problem):
        self.load_meta(competition, volume, semester, issue, problem) \
            .add_id(f'{problem:02d}') \
            .add_number(problem)

        vol = ContextVolume(self.root, competition, volume)
        categories = vol.data['categories']
        self.add(categories=categories[problem - 1])


class ContextRoundFull(ContextRound):
    _subcontext_class = ContextProblem

    def populate(self, competition, volume, semester, issue):
        super().populate(competition, volume, semester, issue)
        count = len(ContextVolume(self.root, competition, volume).data['categories'])

        self.add_list('problems', [
            self._subcontext_class(self.root, competition, volume, semester, issue, problem)
            for problem in range(1, count + 1)
        ])


""" Buildable contexts """


class ContextVolumeBooklet(BuildableFileSystemContext, ContextSeminar):
    def populate(self, root, competition, volume):
        self.adopt(
            module=ContextModule('seminar'),
            competition=ContextCompetition(root, competition),
            volume=ContextVolume(root, competition, volume),
        )


class ContextSemesterBooklet(BuildableFileSystemContext, ContextSeminar):
    def populate(self, root, competition, volume, semester):
        self.adopt(
            module=ContextModule('seminar'),
            competition=ContextCompetition(root, competition),
            volume=ContextVolume(root, competition, volume),
            semester=ContextSemesterFull(root, competition, volume, semester),
        )


class ContextBooklet(BuildableFileSystemContext, ContextSeminar):
    _schema = Schema({})  # nothing inherent to this context
    _validator_class = SeminarRoundValidator

    def populate(self, competition, volume, semester, issue):
        super().populate(competition)

        self.adopt(
            module=ContextModule('seminar'),
            competition=ContextCompetition(self.root, competition),
            volume=ContextVolume(self.root, competition, volume),
            semester=ContextSemester(self.root, competition, volume, semester),
            round=ContextRoundFull(self.root, competition, volume, semester, issue),
        )
