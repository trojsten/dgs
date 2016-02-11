#!/usr/bin/python3.4

import argparse
import json
import os
import datetime

def readableDir(prospectiveDir):
	if not os.path.isdir(prospectiveDir):
		raise Exception("readableDir: {0} is not a valid path".format(prospectiveDir))
	if os.access(prospectiveDir, os.R_OK):
		return prospectiveDir
	else:
		raise Exception("readableDir: {0} is not a readable dir".format(prospectiveDir))



parser = argparse.ArgumentParser(
	description				= "Create booklet recipes for DeGeŠ",
)
parser.add_argument('file', type = argparse.FileType('r'))
parser.add_argument('outDirectory', type = readableDir)
args = parser.parse_args()

settings = json.load(args.file)

with open('{0}/settings.tex'.format(args.outDirectory), 'w+') as output:
	output.write('\\loadSeminar{{{0}}}\n'.format(settings['seminar']))
	output.write('\\RenewDocumentCommand{{\\currentVolume}}{{}}{{{0}}}\n'.format(settings['volume']))
	output.write('\\RenewDocumentCommand{{\\currentPart}}{{}}{{{0}}}\n'.format(settings['part']))
	output.write('\\RenewDocumentCommand{{\\currentSeries}}{{}}{{{0}}}\n'.format(settings['series']))
	output.write('\\RenewDocumentCommand{{\\currentDeadline}}{{}}{{{0}}}\n'.format(
		(datetime.datetime.strptime(settings['deadline'], '%Y-%m-%d').strftime('%d. %m. %Y'))
	))

with open('{0}/tasks/recipe.tex'.format(args.outDirectory), 'w+') as output:
	for task in settings['tasks']:
		output.write("\\addTask{{{0}}}{{{1}}}{{{2}}}\n".format(task['name'], task['pointsDescription'], task['pointsCode']))

with open('{0}/solutions/recipe.tex'.format(args.outDirectory), 'w+') as output:
	for task in settings['tasks']:
		output.write("\\addSolution{{{0}}}{{{1}}}{{{2}}}{{{3}}}\n".format(task['name'], task['solutionBy'], task['evaluationBy'], task['genderSuffix']))
