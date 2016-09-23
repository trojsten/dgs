#!/usr/bin/python3

import os, re, datetime, argparse, shutil, json, colorama
from colorama import Fore as cf

colorama.init()

VERSION = "1.00"
DATE = "2016-09-11"

def init():
    print(cf.BLUE + "This is DeGeŠ-prepare, version " + cf.MAGENTA + VERSION + cf.BLUE + " [" + cf.MAGENTA + DATE + cf.BLUE + "]")
    print(cf.BLUE + "File " + cf.CYAN + root)

def processJSON(fileJSON):
    try:
        settings = json.load(open(fileJSON, 'r+'))
    except FileNotFoundError as e:
        abort("Series configuration file " + cf.CYAN + fileJSON + cf.RED + " could not be found")

    try:
        with open('input/settings.tex', 'w+') as output:
            output.write('\\RenewDocumentCommand{{\\currentVolume}}{{}}{{{0}}}\n'.format(settings['volume']))
            output.write('\\RenewDocumentCommand{{\\rootDirectory}}{{}}{{{0}}}\n'.format(root))
            output.write('\\RenewDocumentCommand{{\\currentPart}}{{}}{{{0}}}\n'.format(settings['part']))
            output.write('\\RenewDocumentCommand{{\\currentRound}}{{}}{{{0}}}\n'.format(settings['round']))
            output.write('\\RenewDocumentCommand{{\\currentDeadline}}{{}}{{{0}}}\n'.format(
                (datetime.datetime.strptime(settings['deadline'], '%Y-%m-%d').strftime('%d. %m. %Y'))
            ))
            output.write('\\loadSeminar{{{0}}}\n'.format(settings['seminar']))
             
        with open('{root}/recipe-problems.tex'.format(root = root), 'w+') as output:
            for problem in settings['problems']:
                output.write("\\addProblem{{{0}}}{{{1}}}{{{2}}}\n".format(problem['name'], problem['pointsDescription'], problem['pointsCode']))

        with open('{root}/recipe-solutions.tex'.format(root = root), 'w+') as output:
            for problem in settings['problems']:
                output.write("\\addSolution{{{0}}}{{{1}}}{{{2}}}{{{3}}}\n".format(problem['name'], problem['solutionBy'], problem['evaluationBy'], problem['genderSuffix']))
    except FileNotFoundError as e:
        abort("Could not write to file: " + cf.CYAN + e)

def bye():
    print(cf.GREEN + "Everything finished successfully, bye")



parser = argparse.ArgumentParser(
    description             = "Prepare and compile a DeGeŠ round from repository",
)
parser.add_argument('file', type = argparse.FileType('r'))
#parser.add_argument('-c', '--clean', action = 'store_true', help = 'Recreate all temporary input files first')
#parser.add_argument('-p', '--purge', action = 'store_true', help = 'Purge all temporary files')
args = parser.parse_args()

fileJSON = args.file.name
root = re.sub('^\./source/', './input/', os.path.dirname(fileJSON))

init()
processJSON(fileJSON)
bye()
