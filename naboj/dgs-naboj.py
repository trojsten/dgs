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
    print("\033[32mThis is DeGeŠ for Náboj, version \033[95m0.01\033[32m [\033[95m2016-08-15\033[32m]\033[0m")
    print("\033[32mInitializing\033[0m")

    try:
        shutil.rmtree('temp/', True)
        shutil.copytree('{0}/'.format(root), 'temp/')

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
    shutil.rmtree('source/{0}/output/'.format(args.volume), True)
    shutil.copytree('output/', 'source/{0}/output/'.format(args.volume), ignore = shutil.ignore_patterns('*.aux', '*.log', '*.out'))

def abort(message):
    print("\033[31m{0}\033[0m".format(message))
    print("\033[31mAborting operation\033[0m")
    exit(1)

def bye():
    print("\033[32mEverything finished successfully, bye\033[0m")

def processJSON():
    try:
        configFile = 'source/{0}/problems/settings.json'.format(args.volume)
        settings = json.load(open(configFile, 'r+'))
    except FileNotFoundError as e:
        abort("Series configuration file \033[96m{0}\033[31m could not be found".format(configFile))
    
    try:
        with open('input/settings.tex', 'w+') as output:
            output.write('\\loadSeminar{fks}\n')
            output.write('\\loadLanguage{{{0}}}\n'.format(args.language))
            output.write('\\RenewDocumentCommand{{\\currentVolume}}{{}}{{{0}}}\n'.format(args.volume))

        with open('input/recipe-booklet-problems.tex', 'w+') as output:
            for number, problem in enumerate(settings['problems']):
                output.write("\\addProblem{{{0}}}{{{1}}}\n".format(number + 1, problem))

        with open('input/recipe-booklet-solutions.tex', 'w+') as output:
            for number, problem in enumerate(settings['problems']):
                output.write("\\addSolution{{{0}}}{{{1}}}\n".format(number + 1, problem))
        
        with open('input/recipe-answers.tex', 'w+') as output:
            papers = [[], [], [], [], []]
            for number, problem in enumerate(settings['problems']):
                papers[(number + 1) % 5].append((number + 1, problem))

            for paper in papers:
                for number, problem in paper:
                    output.write("\\addAnswer{{{0}}}{{{1}}}\n".format(number, problem))
                output.write("\\newpage\n")

    except FileNotFoundError as e:
        abort("Could not write to file: \033[94m{0}\033[0m".format(e))


parser = argparse.ArgumentParser(
    description             = "Prepare and compile a Náboj volume from repository",
)
parser.add_argument('volume', type = int)
parser.add_argument('language', choices = ['english', 'slovak', 'czech', 'hungarian', 'polish'])
parser.add_argument('-c', '--clean', action = 'store_true', help = 'call \'make distclean\' first')
parser.add_argument('-y', '--copy', action = 'store_true', help = 'copy output back to the repository')
args = parser.parse_args()
root = 'source/{0}/problems/{1}'.format(args.volume, args.language)

if args.clean:
    clean()

init()
processJSON()

if os.system('make') != 0:
    abort("make failed")
    exit(1)
else:
    print("\033[32mmake returned 0\033[0m") 

if args.copy:
    copyBack()

bye()
