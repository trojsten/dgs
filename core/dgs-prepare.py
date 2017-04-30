#!/usr/bin/python3

import sys, os, re, datetime, argparse, shutil, yaml, fnmatch, colorama
from colorama import Fore as cf

colorama.init()

VERSION = "2.00"
DATE = "2017-02-26"

def init():
    print(cf.BLUE + "This is DeGeŠ-prepare, version " + cf.MAGENTA + VERSION + cf.BLUE + " [" + cf.MAGENTA + DATE + cf.BLUE + "]")
    print(cf.BLUE + "Invoked on file " + cf.MAGENTA + args.file.name + cf.RESET)

def abortError(e):
    print(cf.RED + e.strerror + cf.WHITE)
    sys.exit(3)

def climbUp(level):
    return os.path.abspath(os.path.join(os.path.dirname(rootFile), *(['..'] * level)))

def metadataFile(level):
    return os.path.abspath(os.path.join(os.path.join(climbUp(level)), 'meta.yaml'))

def protectedLoad(fileName):
    try:
        return yaml.load(open(fileName, 'r+'))
    except FileNotFoundError as e:
        print(cf.RED + "File not found: {}".format(fileName) + cf.WHITE)
        sys.exit(2)
    except yaml.YAMLError as e:
        print(cf.RED + "Could not parse YAML file {}".format(fileName) + cf.WHITE)
        sys.exit(3)

def superstructure(level):
    name = os.path.basename(os.path.normpath(climbUp(level)))
    content = protectedLoad(metadataFile(level))
    return (name, content) 

def processMetadata():
    moduleName, moduleConf      = superstructure(3)
    volumeName, volumeConf      = superstructure(2)
    semesterName, semesterConf  = superstructure(1)
    roundName, roundConf        = superstructure(0)
    problems                    = []


    for directory in sorted(os.listdir(rootDir)):
        fullName = os.path.join(rootDir, directory)
        if os.path.isdir(fullName):
            problems.append(protectedLoad(os.path.join(fullName, 'meta.yaml')))

    print(rootFile)
    print(rootDir)
    print(inputRootDir)

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
