import datetime

from pathlib import Path
from abc import ABCMeta
from schema import Schema, Optional, Use, And, Or

from core.builder.context import FileSystemContext, BuildableContext, ContextModule


class ContextSeminar(FileSystemContext, metaclass=ABCMeta):
    def ident(self, competition=None, volume=None, semester=None, round=None, problem=None):
        return (
            self.default(competition),
            self.default(volume, lambda x: f'{x:02d}'),
            self.default(semester, str),
            self.default(round, str),
            self.default(problem, lambda x: f'{x:02d}'),
        )

    def node_path(self, competition=None, volume=None, semester=None, round=None, problem=None):
        return Path(self.root, *self.ident(competition, volume, semester, round, problem))


class ContextCompetition(ContextSeminar):
    schema = Schema({
        'id': And(str, len),
        'short': And(str, len),
        'full': Schema({
            'nominative': And(str, len),
            Optional('genitive'): And(str, len),
            Optional('locative'): And(str, len),
        }),
        'urls': Schema({
            'web': And(str, len),       # set this to URL
            'submit': And(str, len),    # and here too
        }),
        'language': And(Use(str), lambda x: x in ['sk', 'cs', 'en', 'pl', 'hu', 'es', 'ru', 'de']),
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
    schema = Schema({
        'id': str,
        'number': int,
        Optional('categories'): [[], [str]],
    })

    def populate(self, competition, volume):
        self.load_meta(competition, volume) \
            .add_id(f'{volume:02d}') \
            .add_number(volume)


class ContextSemester(ContextSeminar):
    schema = Schema({
        'id': And(str, len),
        'number': And(int, lambda x: x in [1, 2]),
        'neuter': Schema({'nominative': str, 'genitive': str}),
        'feminine': Schema({'nominative': str, 'genitive': str}),
    })

    def populate(self, competition, volume, semester):
        self.id = str(semester)
        self.load_meta(competition, volume, semester) \
            .add_id(self.id) \
            .add_number(semester)
        # Add fancy names for the semesters
        self.add({
            'neuter': {
                'nominative': ['zimné', 'letné'][semester - 1],
                'genitive': ['zimného', 'letného'][semester - 1],
            },
            'feminine': {
                'nominative': ['zimná', 'letná'][semester - 1],
                'genitive': ['zimnej', 'letnej'][semester - 1],
            },
        })


class ContextSemesterFull(ContextSemester):
    def populate(self, root, competition, volume, semester):
        self.add_children(ContextRoundFull, 'rounds', (root, competition, volume, semester))


class ContextRound(ContextSeminar):
    defaults = {
        'instagram': {
            'skin': 'orange',
            'textColour': 'black',
        }
    }

    schema = Schema({
        'deadline': datetime.date,
        Optional('instagram'): Schema({
            'skin': Use(str, lambda x: x in ['orange', 'grey']),
            'textColour': str,
        }),
        'id': And(str, len),
        'number': int,
    })

    def populate(self, competition, volume, semester, round):
        self.load_meta(competition, volume, semester, round) \
            .add_id(str(round)) \
            .add_number(round)


class ContextRoundFull(ContextRound):
    def populate(self, competition, volume, semester, round):
        super().populate(competition, volume, semester, round)
        count = len(ContextVolume(self.root, competition, volume).data['categories'])

        self.add_list('problems', [
            ContextProblem(self.root, competition, volume, semester, round, problem)
            for problem in range(1, count + 1)
        ])


class ContextProblem(ContextSeminar):
    schema = Schema({
        'title': And(str, len),
        'categories': list,
        'number': And(int, lambda x: x >= 1 and x <= 8),
        'id': str,
        'evaluation': Or('', And(str, len), list, dict),
        'solution': Or('', And(str, len), list, dict),
        'points': Schema({
            'description': And(int, lambda x: x >= 0),
            Optional('code'): And(int, lambda x: x >= 0),
            Optional('extra'): And(int, lambda x: x >= 0),
        }),

    })

    def populate(self, competition, volume, semester, round, problem):
        self.load_meta(competition, volume, semester, round, problem) \
            .add_id(f'{problem:02d}') \
            .add_number(problem)

        vol = ContextVolume(self.root, competition, volume)
        categories = vol.data['categories']
        self.add({'categories': categories[problem - 1]})


""" Buildable contexts """


class ContextVolumeBooklet(ContextSeminar):
    def populate(self, root, competition, volume):
        self.adopt('module', ContextModule('seminar'))
        self.adopt('competition', ContextCompetition(root, competition))
        self.adopt('volume', ContextVolume(root, competition, volume))


class ContextSemesterBooklet(ContextSeminar):
    def populate(self, root, competition, volume, semester):
        self.adopt('module', ContextModule('seminar'))
        self.adopt('competition', ContextCompetition(root, competition))
        self.adopt('volume', ContextVolume(root, competition, volume))
        self.adopt('semester', ContextSemesterFull(root, competition, volume, semester))


class ContextBooklet(BuildableContext, ContextSeminar):
    schema = Schema({})  # fix this

    def populate(self, competition, volume, semester, round):
        self.adopt('module', ContextModule('seminar'))
        self.adopt('competition', ContextCompetition(self.root, competition))
        self.adopt('volume', ContextVolume(self.root, competition, volume))
        self.adopt('semester', ContextSemester(self.root, competition, volume, semester))
        self.adopt('round', ContextRoundFull(self.root, competition, volume, semester, round))
