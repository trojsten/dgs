#!/usr/bin/python3

import sys, os, re, datetime, argparse, shutil, yaml, fnmatch, colorama
from colorama import Fore as cf

colorama.init()

VERSION = "2.00"
DATE = "2017-02-26"

def init():
    print(cf.BLUE + "This is DeGeŠ-prepare, version " + cf.MAGENTA + VERSION + cf.BLUE + " [" + cf.MAGENTA + DATE + cf.BLUE + "]")
    print(cf.BLUE + "Invoked on file " + cf.CYAN + args.file.name + cf.WHITE)



def abortError(e):
    print("{}: {}".format(cf.RED + e.strerror + cf.WHITE))
    sys.exit(3)

def climbUp(level):
    return os.path.abspath(os.path.join(os.path.dirname(rootFile), *(['..'] * level)))

def metadataFile(level, fileName):
    return os.path.abspath(os.path.join(os.path.join(climbUp(level)), fileName))

def protectedLoad(fileName):
    try:
        return yaml.load(open(fileName, 'r+'))
    except FileNotFoundError as e:
        print(cf.RED + "File not found: {}".format(fileName) + cf.WHITE)
        sys.exit(2)
    except yaml.YAMLError as e:
        print(cf.RED + "Could not parse YAML file {}".format(fileName) + cf.WHITE)
        sys.exit(3)

def superstructure(level, fileName):
    name = os.path.basename(os.path.normpath(climbUp(level)))
    content = protectedLoad(metadataFile(level, fileName))
    return (name, content) 

def processMetadata():
    module, moduleConf      = superstructure(3, 'module.yaml')
    volume, volumeConf      = superstructure(2, 'volume.yaml')
    semester, semesterConf  = superstructure(1, 'semester.yaml')
    round, roundConf        = superstructure(0, 'round.yaml')
    problems                = []


    for directory in sorted(os.listdir(rootDir)):
        fullName = os.path.join(rootDir, directory)
        if os.path.isdir(fullName):
            problems.append(protectedLoad(os.path.join(fullName, 'meta.yaml')))

    print(rootFile)
    print(rootDir)
    print(inputRootDir)

    try:
        with open('input/settings.tex', 'w+') as output:
            output.write('\\RenewDocumentCommand{{\\rootDirectory}}{{}}{{{0}}}\n'.format(inputRootDir))
            output.write('\\RenewDocumentCommand{{\\currentVolume}}{{}}{{{0}}}\n'.format(volume))
            output.write('\\RenewDocumentCommand{{\\currentSemester}}{{}}{{{0}}}\n'.format(semester))
            output.write('\\RenewDocumentCommand{{\\currentRound}}{{}}{{{0}}}\n'.format(round))
            output.write('\\RenewDocumentCommand{{\\currentDeadline}}{{}}{{{0}}}\n'.format(roundConf['deadline'].strftime('%d. %m. %Y')))
            output.write('\\loadSeminar{{{0}}}\n'.format(module))
             
        with open('{root}/recipe-problems.tex'.format(root = inputRootDir), 'w+') as output:
            for problem in problems:
                output.write("\\addProblem{{{0}}}{{{1}}}{{{2}}}\n".format(problem['name'], problem['pointsDescription'], problem['pointsCode']))

        with open('{root}/recipe-solutions.tex'.format(root = inputRootDir), 'w+') as output:
            for problem in problems:
                output.write("\\addSolution{{{0}}}{{{1}}}{{{2}}}{{{3}}}\n".format(problem['name'], problem['solutionBy'], problem['evaluation'], problem['genderSuffix']))
    except FileNotFoundError as e:
        abort("Could not write to file: " + cf.CYAN + e)

def bye():
    print(cf.GREEN + "Everything finished successfully, bye")



parser = argparse.ArgumentParser(
    description             = "Prepare and compile a DeGeŠ XeLaTeX template for a single round from repository",
)
parser.add_argument('file', type = argparse.FileType('r'), help = 'round\'s YAML metadata file')
args = parser.parse_args()

rootFile = args.file.name
rootDir = os.path.dirname(rootFile)
inputRootDir = re.sub('source/', 'input/', os.path.dirname(rootFile))

init()
processMetadata()

bye()
