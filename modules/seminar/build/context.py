import os
import sys
import collections
from pathlib import Path

sys.path.append('.')

from core.utilities import context


class ContextSeminar(context.Context):
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
    def __init__(self, root, competition):
        super().__init__()
        self.load_meta(root, competition).add_id(competition)


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
        # Currently missing: fill in rounds and such
        # This will be useful for invites


class ContextRound(ContextSeminar):
    def __init__(self, root, competition, volume, semester, round):
        super().__init__()
        self.id = str(round)
        self.load_meta(root, competition, volume, semester, round) \
            .add_id(self.id) \
            .add_number(round)


class ContextRoundFull(ContextRound):
    def __init__(self, root, competition, volume, semester, round):
        super().__init__(root, competition, volume, semester, round)

        comp = ContextCompetition(root, competition)
        problems = collections.OrderedDict()

        for p in range(0, len(comp.data['categories'])):
            pn = f'{(p + 1):02d}'
            problems[pn] = ContextProblem(root, competition, volume, semester, round, p + 1).data

        self.add({'problems': problems})


class ContextProblem(ContextSeminar):
    def __init__(self, root, competition, volume, semester, round, problem):
        super().__init__()
        self.id = f'{problem:02d}'
        self.load_meta(root, competition, volume, semester, round, problem) \
            .add_id(self.id) \
            .add_number(problem)

        comp = ContextCompetition(root, competition)
        self.add({'categories': comp.data['categories'][problem - 1]})


class ContextBooklet(ContextSeminar):
    def __init__(self, root, competition, volume, semester, round):
        super().__init__()
        self.absorb('module', ContextModule('seminar'))

        if competition is not None:
            self.absorb('competition', ContextCompetition(root, competition))
        if volume is not None:
            self.absorb('volume', ContextVolume(root, competition, volume))
        if semester is not None:
            self.absorb('semester', ContextSemester(root, competition, volume, semester))
        if round is not None:
            self.absorb('round', ContextRoundFull(root, competition, volume, semester, round))


class ContextInvite(ContextSeminar):
    def __init__(self, root, competition, volume, semester):
        super().__init__()
        self.absorb('module', ContextModule('seminar'))

        if competition is not None:
            self.absorb('competition', ContextCompetition(root, competition))
        if volume is not None:
            self.absorb('volume', ContextVolume(root, competition, volume))
        if semester is not None:
            self.absorb('semester', ContextSemester(root, competition, volume, semester))
