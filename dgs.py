#!/usr/bin/python3.4

import os, re, datetime, argparse, shutil, json

def readableDir(prospectiveDir):
    if not os.path.isdir(prospectiveDir):
        raise Exception("readableDir: {0} is not a valid path".format(prospectiveDir))
    if os.access(prospectiveDir, os.R_OK):
        return prospectiveDir
    else:
        raise Exception("readableDir: {0} is not a readable dir".format(prospectiveDir))

def init():
    print("\033[32mThis is DeGeŠ, version \033[95m1.00\033[32m [\033[95m2016-09-08\033[32m]\033[0m")
    print("\033[32mInitializing\033[0m")

    try:
        os.makedirs('{root}/input'.format(root = root))
        os.makedirs('{root}/output'.format(root = root))
    except os.error as e:
        print("Directories already present")

    try:
        os.symlink('{here}/core/'.format(here = os.path.dirname(os.path.realpath(__file__))), '{root}/core'.format(root = root))
    except FileExistsError as e:
        print("Core already linked")

    try:
        os.symlink('{here}/Makefile'.format(here = os.path.dirname(os.path.realpath(__file__))), '{root}/Makefile'.format(root = root))
    except FileExistsError as e:
        print("Makefile already linked")

    print("\033[32mDirectories have been created\033[0m")

def clean():
    print("\033[32mCleaning up\033[0m")

    shutil.rmtree('{root}/input/'.format(root = root), True)
    shutil.rmtree('{root}/output/'.format(root = root), True)

    os.unlink('{root}/Makefile'.format(root = root))
    os.unlink('{root}/core'.format(root = root))

def abort(message):
    print("\033[31m{0}\033[0m".format(message))
    print("\033[31mAborting operation\033[0m")
    exit(1)

def bye():
    print("\033[32mEverything finished successfully, bye\033[0m")

def processJson():
    try:
        configFile = '{root}/source/settings.json'.format(root = root)
        settings = json.load(open(configFile, 'r+'))
    except FileNotFoundError as e:
        abort("Series configuration file \033[96m{0}\033[31m could not be found".format(configFile))

    
    for number, problem in enumerate(settings['problems']):
       for inout in ['in', 'out']:
            directory = '{root}/{prefix}put/{problem:02d}'.format(root = root, prefix = inout, problem = number + 1)
            if not os.path.exists(directory):
               os.makedirs(directory)

    try:
        with open('{root}/input/settings.tex'.format(root = root), 'w+') as output:
            output.write('\\loadSeminar{{{0}}}\n'.format(settings['seminar']))
            output.write('\\RenewDocumentCommand{{\\currentVolume}}{{}}{{{0}}}\n'.format(settings['volume']))
            output.write('\\RenewDocumentCommand{{\\currentPart}}{{}}{{{0}}}\n'.format(settings['part']))
            output.write('\\RenewDocumentCommand{{\\currentRound}}{{}}{{{0}}}\n'.format(settings['round']))
            output.write('\\RenewDocumentCommand{{\\currentDeadline}}{{}}{{{0}}}\n'.format(
                (datetime.datetime.strptime(settings['deadline'], '%Y-%m-%d').strftime('%d. %m. %Y'))
            ))

        with open('{root}/input/recipe-problems.tex'.format(root = root), 'w+') as output:
            for problem in settings['problems']:
                output.write("\\addProblem{{{0}}}{{{1}}}{{{2}}}\n".format(problem['name'], problem['pointsDescription'], problem['pointsCode']))

        with open('{root}/input/recipe-solutions.tex'.format(root = root), 'w+') as output:
            for problem in settings['problems']:
                output.write("\\addSolution{{{0}}}{{{1}}}{{{2}}}{{{3}}}\n".format(problem['name'], problem['solutionBy'], problem['evaluationBy'], problem['genderSuffix']))
    except FileNotFoundError as e:
        abort("Could not write to file: \033[94m{0}\033[0m".format(e))



parser = argparse.ArgumentParser(
    description             = "Prepare and compile a DeGeŠ round from repository",
)
parser.add_argument('seminar', choices = ['fks', 'kms', 'ksp', 'ufo', 'prask', 'fx'])
parser.add_argument('volume', type = int)
parser.add_argument('part', type = int, choices = [1, 2])
parser.add_argument('round', type = int, choices = [1, 2, 3]) 
parser.add_argument('-c', '--clean', action = 'store_true', help = 'Recreate all temporary input files first')
parser.add_argument('-p', '--purge', action = 'store_true', help = 'Purge all temporary files')

args = parser.parse_args()
root = 'source/{0}/{1:02d}/{2}/{3}'.format(args.seminar, args.volume, args.part, args.round)

if args.clean:
    clean()

if args.purge:
    clean()
    exit(0)

init()
processJson()

if os.system('make -C {root}'.format(root = root)) != 0:
    abort("make failed")
    exit(1)
else:
    print("\033[32mmake returned 0\033[0m") 

bye()
