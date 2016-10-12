#!/usr/bin/python3.4

import os, re, datetime, argparse, shutil, json

def init():
    print("\033[32mThis is DeGeŠ for Náboj, version \033[95m0.27\033[32m [\033[95m2016-09-06\033[32m]\033[0m")
    print("\033[32mInitializing\033[0m")


def processJSON(fileJSON):
    try:
        settings = json.load(open(fileJSON, 'r+'))
    except FileNotFoundError as e:
        abort("Series configuration file " + cf.CYAN + fileJSON + cf.RED + " could not be found")
    
    try:
        with open('input/settings.tex', 'w+') as output:
            output.write('\\RenewDocumentCommand{{\\rootDirectory}}{{}}{{{0}}}\n'.format(root))
            output.write('\\loadLanguage{{{0}}}\n'.format(args.language))
            output.write('\\loadSeminar{fks}\n')
            output.write('\\RenewDocumentCommand{{\\currentVolume}}{{}}{{{0}}}\n'.format(settings['volume']))
                       
        with open('{root}/recipe-booklet-problems.tex'.format(root = root), 'w+') as output:
            for number, problem in enumerate(settings['problems']):
                output.write("\\addProblem{{{0}}}{{{1}}}\n".format(number + 1, problem))

        with open('{root}/recipe-booklet-solutions.tex'.format(root = root), 'w+') as output:
            for number, problem in enumerate(settings['problems']):
                output.write("\\addSolution{{{0}}}{{{1}}}\n".format(number + 1, problem))
        
        with open('{root}/recipe-answers.tex'.format(root = root), 'w+') as output:
            papers = [[], [], [], [], []]
            for number, problem in enumerate(settings['problems']):
                papers[(number + 1) % 5].append((number + 1, problem))

            for paper in papers:
                for number, problem in paper:
                    output.write("\\addAnswer{{{0}}}{{{1}}}\n".format(number, problem))
                output.write("\\newpage\n")

        with open('{root}/recipe-tearoff.tex'.format(root = root), 'w+') as output:
            teams = [settings['teams'][i*3 : i*3 + 3] for i in range((len(settings['teams']) + 2) // 3)]

            for triplet in teams:
                for number, problem in enumerate(settings['problems']):
                    for team in triplet:
                        output.write("\\addTearoff{{{number}}}{{{problem}}}{{{team}}}{{{language}}}\n".format(number = number + 1, problem = problem, team = team['id'], language = team['language']))
                    output.write("\\newpage\n")

    except FileNotFoundError as e:
        abort("Could not write to file " + cf.CYAN + e)

def bye():
    print("\033[32mEverything finished successfully, bye\033[0m")


parser = argparse.ArgumentParser(
    description             = "Prepare and compile a Náboj volume from repository",
)
parser.add_argument('language', choices = ['english', 'slovak', 'czech', 'hungarian', 'polish'])
parser.add_argument('file', type = argparse.FileType('r'))
args = parser.parse_args()

fileJSON = args.file.name
root = re.sub('^\./source/', './input/', os.path.dirname(fileJSON))

init()
processJSON(fileJSON)
bye()
