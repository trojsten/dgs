import os
import sys
import collections
import datetime

from pathlib import Path
from abc import ABCMeta, abstractmethod
from schema import Schema, Optional, Use, And, Or

from core.builder import context


class ContextSeminar(context.Context, metaclass=ABCMeta):
    def node_path(self, root, competition=None, volume=None, semester=None, round=None, problem=None):
        return Path(
            root,
            '' if competition is None else competition,
            '' if volume is None else f'{volume:02d}',
            '' if semester is None else str(semester),
            '' if round is None else str(round),
            '' if problem is None else f'{problem:02d}',
        )


class ContextModule(ContextSeminar):
    def __init__(self, module):
        super().__init__()
        self.add_id(module)


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
            'web': And(str, len), # set this to URL
            'submit': And(str, len), # and here too
        }),
        'language': And(Use(str), lambda x: x in ['sk', 'cs', 'en', 'pl', 'hu', 'es', 'ru', 'de']),
        'categories': list,
        'founded': int,
        Optional('email'): str,
        Optional('hacks'): dict,
        'head': Schema({
            'name': And(str, len),
            'email': And(str, len),  # change this to email
            'phone': And(str, len),  # change this to phone regex
        }),
        'organisation': dict,
    })

    def __init__(self, root, competition):
        super().__init__()
        self.load_meta(root, competition) \
            .add_id(competition)
        self.validate()


class ContextVolume(ContextSeminar):
    def __init__(self, root, competition, volume):
        super().__init__()
        self.id = f'{volume:02d}'
        self.load_meta(root, competition, volume) \
            .add_id(self.id) \
            .add_number(volume)


class ContextSemester(ContextSeminar):
    def __init__(self, root, competition, volume, semester):
        super().__init__()
        self.id = str(semester)
        self.load_meta(root, competition, volume, semester) \
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
    def __init__(self, root, competition, volume, semester):
        super().__init__(root, competition, volume, semester)
        self.add_children(ContextRoundFull, 'rounds', (root, competition, volume, semester))


class ContextRound(ContextSeminar):
    schema = Schema([
        {
            'deadline': datetime.datetime,
            Optional('instagram'): dict(
                skin=Use(str, lambda x: x in ['orange', 'grey']),
                textColour=Use(str),
            )
        }
    ])

    def __init__(self, root, competition, volume, semester, round):
        super().__init__()
        self.id = str(round)
        self.load_meta(root, competition, volume, semester, round) \
            .add_id(self.id) \
            .add_number(round)


class ContextRoundFull(ContextRound):
    defaults = {
        'instagram': {
            'skin': 'orange',
            'textColour': 'black',
        }
    }

    def __init__(self, root, competition, volume, semester, round):
        super().__init__(root, competition, volume, semester, round)
        self.add(self.defaults)

        vol = ContextVolume(root, competition, volume)
        categories = vol.data['categories']
        problems = collections.OrderedDict()

        for p in range(0, len(categories)):
            pn = f'{(p + 1):02d}'
            problems[pn] = ContextProblem(root, competition, volume, semester, round, p + 1).data

        self.add({'problems': problems})


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
        }),

    })

    def __init__(self, root, competition, volume, semester, round, problem):
        super().__init__()
        self.id = f'{problem:02d}'
        self.load_meta(root, competition, volume, semester, round, problem) \
            .add_id(self.id) \
            .add_number(problem)

        vol = ContextVolume(root, competition, volume)
        categories = vol.data['categories']
        self.add({'categories': categories[problem - 1]})
        self.validate()


""" Buildable contexts """


class ContextVolumeBooklet(ContextSeminar):
    def __init__(self, root, competition, volume):
        super().__init__()
        self.adopt('module', ContextModule('seminar'))
        self.adopt('competition', ContextCompetition(root, competition))
        self.adopt('volume', ContextVolume(root, competition, volume))


class ContextSemesterBooklet(ContextSeminar):
    def __init__(self, root, competition, volume, semester):
        super().__init__()
        self.adopt('module', ContextModule('seminar'))
        self.adopt('competition', ContextCompetition(root, competition))
        self.adopt('volume', ContextVolume(root, competition, volume))
        self.adopt('semester', ContextSemesterFull(root, competition, volume, semester))


class ContextBooklet(ContextSeminar):
    def __init__(self, root, competition, volume, semester, round):
        super().__init__()
        self.adopt('module', ContextModule('seminar'))
        self.adopt('competition', ContextCompetition(root, competition))
        self.adopt('volume', ContextVolume(root, competition, volume))
        self.adopt('semester', ContextSemester(root, competition, volume, semester))
        self.adopt('round', ContextRoundFull(root, competition, volume, semester, round))
