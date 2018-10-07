import os, sys, pprint, collections

sys.path.append('.')
import core.utilities.jinja as jinja
import core.utilities.dicts as dicts
import core.utilities.colour as c
import core.utilities.argparser as argparser
import core.utilities.context as context

class ContextSeminar(context.Context):
    def __init__(self, root, course, year, issue):
        super().__init__()
        self.root   = root
        self.course = course
        self.year   = year
        self.issue  = issue

        self.absorb('module',       ContextModule   ('seminar'))
        self.absorb('competition',  ContextCourse   (root, competition))
        self.absorb('volume',       ContextYear     (root, competition, volume))

class ContextRound(ContextSeminar):
    def __init__(self, root, course, year, issue):
        super().__init__(root, course, year, issue)
        self.absorb('issue',    ContextIssue    (root, course, year, 'handouts', issue))

class ContextSemester(ContextSeminar):
    def __init__(self, root, course, year, issue):
        super().__init__(root, course, year, issue)
        self.absorb('issue',    ContextIssue    (root, course, year, 'homework', issue))

class ContextModule(context.Context):
    def __init__(self, module):
        super().__init__()
        self.addId(module)

class ContextCompetition(context.Context):
    def __init__(self, root, competition):
        super().__init__()
        self.loadMeta(root, competition).addId(competition)
        
class ContextVolume(context.Context):
    def __init__(self, root, competition, volume):
        super().__init__()
        id = '{:02d}'.format(volume)
        self.loadMeta(root, competition, '{:02d}'.format(volume)).addId(id)

class ContextIssue(context.Context):
    def __init__(self, root, competition, volume, semester):
        super().__init__()
        id = '{:02d}'.format(issue)
        self.loadYaml(root, course, '{:04d}'.format(year), target, id, 'meta.yaml').addId(id).addNumber(issue)
   


class ContextBooklet(context.Context):
    def __init__(self, root, competition, volume, semester, round):
        super().__init__()
        print(root)
        self.absorb('module',       ContextModule       ('seminar'))
        self.absorb('competition',  ContextCompetition  (root, competition))
        self.absorb('volume',       ContextVolume       (root, competition, volume))
        self.absorb('semester',     ContextSemester     (root, competition, volume, semester))
        self.absorb('round',        ContextRound        (root, competition, volume, semester, round))

def createSeminarParser():
    parser = argparser.createGenericParser()
    parser.add_argument('-c', '--competition', choices = ['FKS', 'KMS', 'UFO', 'KSP', 'Prask', 'FX'])
    parser.add_argument('-v', '--volume',      type = int)
    parser.add_argument('-s', '--semester',    type = int)
    parser.add_argument('-r', '--round',       type = int)
    return parser

def nodePathSeminar(root, competition = None, volume = None, semester = None, round = None, problem = None):
    return os.path.join(
        root,
        '' if competition is None else  competition,
        '' if volume is None else       '{:02d}'.format(volume),
        '' if semester is None else     str(semester),
        '' if round is None else        str(round),
        '' if problem is None else      '{:02d}'.format(problem),
    )

def moduleContext():
    return {
        'id': 'seminar',
    }

def competitionContext(root, competition):
    return context.mergeDicts(context.loadMeta(nodePathSeminar, (root, competition)), {
        'id': competition,
    })

def volumeContext(root, competition, volume):
    vol = context.loadMeta(nodePathSeminar, (root, competition, volume))
    return context.mergeDicts(vol, {
        'id': volume,
        'number': int(volume),
    })

def semesterContext(root, competition, volume, semester):
    directory = nodePathSeminar(root, competition, volume, semester)
    rounds = OrderedDict()

    for child in context.listChildNodes(directory):
        rounds[child] = roundContext(root, competition, volume, semester, child)

    return dicts.merge(context.loadMeta(nodePathSeminar, (root, competition, volume, semester)), {
        'id': str(semester),
        'number':           semester,
        'nominative':       'zimná' if semester == 1 else 'letná',
        'nominativeNeuter': 'zimné' if semester == 1 else 'letné',
        'genitive':         'zimnej' if semester == 1 else 'letnej',
        'rounds':           rounds,
    })

def roundContext(root, competition, volume, semester, round):
    comp = context.loadMeta(nodePathSeminar, (root, competition))
    problems = OrderedDict()
    for p in range(0, len(comp['categories'])):
        pn = '{:02d}'.format(p + 1)
        problems[pn] = problemContext(root, competition, volume, semester, round, p + 1)

    return context.mergeDicts(context.loadMeta(nodePathSeminar, (root, competition, volume, semester, round)), {
        'id': round,
        'number': round,
        'problems': problems,
    })

def problemContext(root, competition, volume, semester, round, problem):
    comp = context.loadMeta(nodePathSeminar, (root, competition))

    return context.mergeDicts(context.loadMeta(nodePathSeminar, (root, competition, volume, semester, round, problem)), {
        'id': '{:02d}'.format(problem),
        'number': problem,
        'categories': comp['categories'][problem - 1],
    })

def bookletContext(root, competition = None, volume = None, semester = None, round = None):
    booklet = {
        'module': moduleContext()
    }
    if competition  is not None:
        booklet['competition']  = competitionContext    (root, competition)
    if volume       is not None:
        booklet['volume']       = volumeContext         (root, competition, volume)
    if semester     is not None:
        booklet['semester']     = semesterContext       (root, competition, volume, semester)
    if round        is not None:
        booklet['round']        = roundContext          (root, competition, volume, semester, round)

    return booklet

def buildInviteContext(root, competition, volume, semester):
    invite = {
        'module': moduleContext()
    }
    invite['competition']       = competitionContext    (root, competition)
    invite['volume']            = volumeContext         (root, competition, volume)
    invite['semester']          = semesterContext       (root, competition, volume, semester)
    invite['semester']['camp']  = loadYaml              (root, competition, volume, str(semester), 'camp.yaml')
    
    return context

