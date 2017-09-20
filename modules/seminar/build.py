#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from utils import *
from colorama import Fore, Style

def buildModuleContext():
    return {
        'id': 'seminar',
    }

def buildCompetitionContext(root, competition):
    return mergeDicts(loadMeta(root, competition), {
        'id': competition,
    })

def buildVolumeContext(root, competition, volume):
    vol = loadMeta(root, competition, volume)
    return mergeDicts(vol, {
        'id': volume,
        'number': int(volume),
    })

def buildSemesterContext(root, competition, volume, semester):
    directory = nodePath(root, competition, volume, semester)
    rounds = {}
    for child in listChildNodes(directory):
        rounds[child] = buildRoundContext(root, competition, volume, semester, child)

    return mergeDicts(loadMeta(root, competition, volume, semester), {
        'id': str(semester),
        'number': semester,
        'nominative':   'zimná' if semester == 1 else 'letná',
        'genitive':     'zimnej' if semester == 1 else 'letnej',
        'rounds': rounds,
    })

def buildRoundContext(root, competition, volume, semester, round):
    comp = loadMeta(root, competition)
    problems = {}
    for p in range(0, len(comp['categories'])):
        pn = '{:02d}'.format(p + 1)
        problems[pn] = buildProblemContext(root, competition, volume, semester, round, p + 1)

    return mergeDicts(loadMeta(root, competition, volume, semester, round), {
        'id': round,
        'number': round,
        'problems': problems,
    })

def buildProblemContext(root, competition, volume, semester, round, problem):
    comp = loadMeta(root, competition)

    return mergeDicts(loadMeta(root, competition, volume, semester, round, problem), {
        'id': '{:02d}'.format(problem),
        'number': problem,
        'categories': comp['categories'][problem - 1],
    })

def buildRoundBookletContext(root, competition, volume, semester, round):
    return {
        'module':           buildModuleContext      (),
        'competition':      buildCompetitionContext (root, competition),
        'volume':           buildVolumeContext      (root, competition, volume),
        'semester':         buildSemesterContext    (root, competition, volume, semester),
        'round':            buildRoundContext       (root, competition, volume, semester, round),
    }

def buildSemesterBookletContext(root, competition, volume, semester):
    return {
        'module':           buildModuleContext      (),
        'competition':      buildCompetitionContext (root, competition),
        'volume':           buildVolumeContext      (root, competition, volume),
        'semester':         buildSemesterContext    (root, competition, volume, semester),
        'round':            buildRoundContext       (root, competition, volume, semester, 1),
    }
