#!/usr/bin/env python3

import argparse, yaml, os, jinja2, sys, pprint, colorama
from utils import *
from collections import OrderedDict
from colorama import Fore, Style

def createXParser():
    parser = argparse.ArgumentParser(
        description             = "Prepare and compile a DeGeŠ seminar competition from repository",
    )
    parser.add_argument('launch',              action = readableDir) 
    parser.add_argument('-c', '--competition', choices = ['FKS', 'KMS', 'UFO', 'KSP', 'Prask', 'FX'])
    parser.add_argument('-v', '--volume',      type = int)
    parser.add_argument('-s', '--semester',    type = int)
    parser.add_argument('-r', '--round',       type = int)
    parser.add_argument('-o', '--output',      action = writeableDir) 
    parser.add_argument('-d', '--debug',       action = 'store_true')
    return parser

def createParser(level):
    parser = argparse.ArgumentParser(
        description             = "Prepare and compile a DeGeŠ seminar competition from repository",
    )
    parser.add_argument('launch',           action = readableDir) 
    if level >= 1:
        parser.add_argument('competition',      choices = ['FKS', 'KMS', 'UFO', 'KSP', 'Prask', 'FX'])
    if level >= 2:
        parser.add_argument('volume',           type = int)
    if level >= 3:
        parser.add_argument('semester',         type = int)
    if level >= 4:
        parser.add_argument('round',            type = int)
    parser.add_argument('-o', '--output',   action = writeableDir) 
    parser.add_argument('-v', '--verbose',  action = 'store_true')
    return parser

def buildFormatTemplate(templateRoot, template, context, outputDirectory = None):
    print(
        jinjaEnv(templateRoot).get_template(template).render(context),
        file = sys.stdout if outputDirectory is None else open(os.path.join(outputDirectory, template), 'w')
    )

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
    rounds = OrderedDict()

    for child in listChildNodes(directory):
        rounds[child] = buildRoundContext(root, competition, volume, semester, child)

    return mergeDicts(loadMeta(root, competition, volume, semester), {
        'id': str(semester),
        'number':       semester,
        'nominative':   'zimná' if semester == 1 else 'letná',
        'nominativeNeuter':   'zimné' if semester == 1 else 'letné',
        'genitive':     'zimnej' if semester == 1 else 'letnej',
        'rounds':       rounds,
    })

def buildRoundContext(root, competition, volume, semester, round):
    comp = loadMeta(root, competition)
    problems = OrderedDict()
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

def buildBookletContext(root, competition = None, volume = None, semester = None, round = None):
    context = {
        'module': buildModuleContext()
    }
    if competition  is not None:
        context['competition']  = buildCompetitionContext   (root, competition)
    if volume       is not None:
        context['volume']       = buildVolumeContext        (root, competition, volume)
    if semester     is not None:
        context['semester']     = buildSemesterContext      (root, competition, volume, semester)
    if round        is not None:
        context['round']        = buildRoundContext         (root, competition, volume, semester, round)

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

