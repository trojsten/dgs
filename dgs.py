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
	print("Initializing")
	os.system('make collect')
	shutil.rmtree('temp/', True)	
	shutil.copytree('{0}/source/'.format(root), 'temp/')

def clean():
	print("Cleaning up...")
	os.system('make distclean')

def copyBack():
	shutil.rmtree('{0}/output/'.format(root), True)
	shutil.copytree('output/', '{0}/output/'.format(root), ignore = shutil.ignore_patterns('*.aux', '*.log', '*.out'))

def processJson():
	settings = json.load(open('{0}/source/settings.json'.format(root), 'r+'))

	with open('input/settings.tex', 'w+') as output:
		output.write('\\loadSeminar{{{0}}}\n'.format(settings['seminar']))
		output.write('\\RenewDocumentCommand{{\\currentVolume}}{{}}{{{0}}}\n'.format(settings['volume']))
		output.write('\\RenewDocumentCommand{{\\currentPart}}{{}}{{{0}}}\n'.format(settings['part']))
		output.write('\\RenewDocumentCommand{{\\currentSeries}}{{}}{{{0}}}\n'.format(settings['series']))
		output.write('\\RenewDocumentCommand{{\\currentDeadline}}{{}}{{{0}}}\n'.format(
			(datetime.datetime.strptime(settings['deadline'], '%Y-%m-%d').strftime('%d. %m. %Y'))
		))

	with open('input/tasks/recipe.tex', 'w+') as output:
		for task in settings['tasks']:
			output.write("\\addTask{{{0}}}{{{1}}}{{{2}}}\n".format(task['name'], task['pointsDescription'], task['pointsCode']))

	with open('input/solutions/recipe.tex', 'w+') as output:
		for task in settings['tasks']:
			output.write("\\addSolution{{{0}}}{{{1}}}{{{2}}}{{{3}}}\n".format(task['name'], task['solutionBy'], task['evaluationBy'], task['genderSuffix']))




parser = argparse.ArgumentParser(
	description				= "Prepare DeGeŠ series from repository",
)
parser.add_argument('seminar', choices = ['fks', 'kms', 'ksp', 'ufo', 'prask', 'fx'])
parser.add_argument('volume', type = int)
parser.add_argument('part', choices = ['autumn', 'spring'])
parser.add_argument('series', type = int, choices = [1, 2, 3]) 
parser.add_argument('-c', '--clean', action = 'store_true', help = 'call \'make distclean\' first')
args = parser.parse_args()
root = 'source/{0}/{1}/{2}/{3}/'.format(args.seminar, args.volume, args.part, args.series)

if args.clean:
	clean()

init()
processJson()

if os.system('make') != 0:
	raise Exception("make did not return 0, aborting")

copyBack()
