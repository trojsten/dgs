import argparse, yaml, os, jinja2, sys, pprint, colorama
from collections import OrderedDict
from colorama import Fore, Style

sys.path.append('.')

import core.builder, build

from core.utils import *

def createSeminarParser():
    parser = core.builder.createGenericParser()
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
    return mergeDicts(loadMeta(nodePathSeminar, (root, competition)), {
        'id': competition,
    })

def volumeContext(root, competition, volume):
    vol = loadMeta(nodePathSeminar, (root, competition, volume))
    return mergeDicts(vol, {
        'id': volume,
        'number': int(volume),
    })

def semesterContext(root, competition, volume, semester):
    directory = nodePathSeminar(root, competition, volume, semester)
    rounds = OrderedDict()

    for child in listChildNodes(directory):
        rounds[child] = build.roundContext(root, competition, volume, semester, child)

    return mergeDicts(loadMeta(nodePathSeminar, (root, competition, volume, semester)), {
        'id': str(semester),
        'number':       semester,
        'nominative':   'zimná' if semester == 1 else 'letná',
        'nominativeNeuter':   'zimné' if semester == 1 else 'letné',
        'genitive':     'zimnej' if semester == 1 else 'letnej',
        'rounds':       rounds,
    })

def roundContext(root, competition, volume, semester, round):
    comp = loadMeta(nodePathSeminar, (root, competition))
    problems = OrderedDict()
    for p in range(0, len(comp['categories'])):
        pn = '{:02d}'.format(p + 1)
        problems[pn] = build.problemContext(root, competition, volume, semester, round, p + 1)

    return mergeDicts(loadMeta(nodePathSeminar, (root, competition, volume, semester, round)), {
        'id': round,
        'number': round,
        'problems': problems,
    })

def problemContext(root, competition, volume, semester, round, problem):
    comp = loadMeta(nodePathSeminar, (root, competition))

    return mergeDicts(loadMeta(nodePathSeminar, (root, competition, volume, semester, round, problem)), {
        'id': '{:02d}'.format(problem),
        'number': problem,
        'categories': comp['categories'][problem - 1],
    })

def bookletContext(root, competition = None, volume = None, semester = None, round = None):
    context = {
        'module': build.moduleContext()
    }
    if competition  is not None:
        context['competition']  = build.competitionContext   (root, competition)
    if volume       is not None:
        context['volume']       = build.volumeContext        (root, competition, volume)
    if semester     is not None:
        context['semester']     = build.semesterContext      (root, competition, volume, semester)
    if round        is not None:
        context['round']        = build.roundContext         (root, competition, volume, semester, round)

    return context

def buildInviteContext(root, competition, volume, semester):
    context = {
        'module': buildModuleContext()
    }
    context['competition']  = buildCompetitionContext   (root, competition)
    context['volume']       = buildVolumeContext        (root, competition, volume)
    context['semester']     = buildSemesterContext      (root, competition, volume, semester)
    context['semester']['camp'] = loadYaml                  (root, competition, volume, str(semester), 'camp.yaml')
    
    return context

