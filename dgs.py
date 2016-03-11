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
    print("\033[32mThis is DeGeŠ, version \033[95m0.41\033[32m [\033[95m2016-02-16\033[32m]\033[0m")
    print("\033[32mInitializing\033[0m")

    try:
        shutil.rmtree('temp/', True)
        shutil.copytree('{0}/source/'.format(root), 'temp/')

        if not os.path.exists('input'):
            os.makedirs('input')

        if not os.path.exists('output'):
            os.makedirs('output')

    except FileNotFoundError as e:
        abort("File not found: \033[94m{0}\033[0m".format(e))

def clean():
    print("\033[32mCleaning up\033[0m")
    os.system('make distclean')

def copyBack():
    print("\033[32mCopying output back to the repository\033[0m")
    shutil.rmtree('{0}/output/'.format(root), True)
    shutil.copytree('output/', '{0}/output/'.format(root), ignore = shutil.ignore_patterns('*.aux', '*.log', '*.out'))

def abort(message):
    print("\033[31m{0}\033[0m".format(message))
    print("\033[31mAborting operation\033[0m")
    exit(1)

def bye():
    print("\033[32mEverything finished successfully, bye\033[0m")

def processJson():
    try:
        configFile = '{0}/source/settings.json'.format(root)
        settings = json.load(open(configFile, 'r+'))
    except FileNotFoundError as e:
        abort("Series configuration file \033[96m{0}\033[31m could not be found".format(configFile))

    
    for number, problem in enumerate(settings['problems']):
       for inout in ['in', 'out']:
            directory = '{0}put/{1:02d}'.format(inout, number + 1)
            if not os.path.exists(directory):
               os.makedirs(directory)

    try:
        with open('input/settings.tex', 'w+') as output:
            output.write('\\loadSeminar{{{0}}}\n'.format(settings['seminar']))
            output.write('\\RenewDocumentCommand{{\\currentVolume}}{{}}{{{0}}}\n'.format(settings['volume']))
            output.write('\\RenewDocumentCommand{{\\currentPart}}{{}}{{{0}}}\n'.format(settings['part']))
            output.write('\\RenewDocumentCommand{{\\currentSeries}}{{}}{{{0}}}\n'.format(settings['series']))
            output.write('\\RenewDocumentCommand{{\\currentDeadline}}{{}}{{{0}}}\n'.format(
                (datetime.datetime.strptime(settings['deadline'], '%Y-%m-%d').strftime('%d. %m. %Y'))
            ))

        with open('input/recipe-problems.tex', 'w+') as output:
            for problem in settings['problems']:
                output.write("\\addProblem{{{0}}}{{{1}}}{{{2}}}\n".format(problem['name'], problem['pointsDescription'], problem['pointsCode']))

        with open('input/recipe-solutions.tex', 'w+') as output:
            for problem in settings['problems']:
                output.write("\\addSolution{{{0}}}{{{1}}}{{{2}}}{{{3}}}\n".format(problem['name'], problem['solutionBy'], problem['evaluationBy'], problem['genderSuffix']))
    except FileNotFoundError as e:
        abort("Could not write to file: \033[94m{0}\033[0m".format(e))



parser = argparse.ArgumentParser(
    description             = "Prepare and compile a DeGeŠ series from repository",
)
parser.add_argument('seminar', choices = ['fks', 'kms', 'ksp', 'ufo', 'prask', 'fx'])
parser.add_argument('volume', type = int)
parser.add_argument('part', choices = ['autumn', 'spring'])
parser.add_argument('series', type = int, choices = [1, 2, 3]) 
parser.add_argument('-c', '--clean', action = 'store_true', help = 'call \'make distclean\' first')
parser.add_argument('-y', '--copy', action = 'store_true', help = 'copy output back to the repository')
args = parser.parse_args()
root = 'source/{0}/{1:02d}/{2}/{3}'.format(args.seminar, args.volume, args.part, args.series)

if args.clean:
    clean()

init()
processJson()

if os.system('make') != 0:
    abort("make failed")
    exit(1)
else:
    print("\033[32mmake returned 0\033[0m") 

if args.copy:
    copyBack()

bye()
