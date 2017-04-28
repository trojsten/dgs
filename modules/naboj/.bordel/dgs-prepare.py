#!/usr/bin/python3.4

import os, re, datetime, argparse, shutil, json

def init():
    print("\033[32mThis is DeGeŠ prepare script for Náboj, version \033[95m1.00\033[32m [\033[95m2016-10-14\033[32m]\033[0m")
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
            output.write('\\RenewDocumentCommand{{\\teamCount}}{{}}{{{0}}}\n'.format(len(settings['teams'][args.language])))
            output.write('\\RenewDocumentCommand{{\\problemCount}}{{}}{{{0}}}\n'.format(len(settings['problems'])))
                       
        with open('{root}/{language}/recipe-booklet-problems.tex'.format(root = root, language = args.language), 'w+') as output:
            for number, problem in enumerate(settings['problems']):
                output.write("\\addProblem{{{0}}}{{{1}}}\n".format(number + 1, problem))

        with open('{root}/{language}/recipe-booklet-solutions.tex'.format(root = root, language = args.language), 'w+') as output:
            for number, problem in enumerate(settings['problems']):
                output.write("\\addSolution{{{0}}}{{{1}}}\n".format(number + 1, problem))
        
        with open('{root}/{language}/recipe-answers-mod5.tex'.format(root = root, language = args.language), 'w+') as output:
            papers = [[], [], [], [], []]
            for number, problem in enumerate(settings['problems']):
                papers[(number + 1) % 5].append((number + 1, problem))

            for paper in papers:
                for number, problem in paper:
                    output.write("\\addAnswer{{{0}}}{{{1}}}\n".format(number, problem))
                output.write("\\newpage\n")
        
        with open('{root}/{language}/recipe-answers.tex'.format(root = root, language = args.language), 'w+') as output:
            for number, problem in enumerate(settings['problems']):
                output.write("\\addAnswer{{{0}}}{{{1}}}\n".format(number + 1, problem))
                if (number % 15 == 14):
                    output.write("\\newpage\n")

        with open('{root}/{language}/recipe-tearoff.tex'.format(root = root, language = args.language), 'w+') as output:
            for number, team in enumerate(settings['teams'][args.language]):
                team['pageorder'] = number + 1

            teams = [settings['teams'][args.language][i*3 : i*3 + 3] for i in range((len(settings['teams'][args.language]) + 2) // 3)]

            for triplet in teams:
                for number, problem in enumerate(settings['problems']):
                    strs = []
                    for team in triplet:
                        strs.append("\\addTearoff{{{number}}}{{{problem}}}{{{team}}}{{{language}}}{{{name}}}{{{page}}}{{{team:06d}{number:03d}}}\n".format(
                            number = number + 1,
                            problem = problem,
                            team = team['id'],
                            name = team['name'],
                            language = args.language, 
                            page = (team['pageorder'] - 1) * len(settings['problems']) + number + 1,
                                                    ))
                    output.write("\hrule\n".join(strs) + "\\newpage\n")
    
        with open('{root}/{language}/barcodes.txt'.format(root = root, language = args.language), 'w+') as output:
            for team in settings['teams'][args.language]:
               for number, problem in enumerate(settings['problems']):
                   output.write("{:06d}{:03d}\n".format(team['id'], number + 1))
                
    except FileNotFoundError as e:
        abort("Could not write to file " + cf.CYAN + e)

def bye():
    print("\033[32mEverything finished successfully, bye\033[0m")


parser = argparse.ArgumentParser(
    description             = "Prepare and compile a Náboj volume from repository",
)
parser.add_argument('language', choices = ['english', 'slovak', 'czech', 'hungarian', 'polish', 'test'])
parser.add_argument('file', type = argparse.FileType('r'))
args = parser.parse_args()

fileJSON = args.file.name
root = re.sub('^\./source/', './input/', os.path.dirname(fileJSON))

init()
processJSON(fileJSON)
bye()
