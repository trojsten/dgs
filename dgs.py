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
	print("This is DeGeŠ, 0.40 [2016-02-15]")
	print("Initializing")
	shutil.rmtree('temp/', True)	
	shutil.copytree('{0}/source/'.format(root), 'temp/')
	os.system("make collect")

def clean():
	print("\033[32mCleaning up\033[0m")
	os.system('make distclean')

def copyBack():
	print("\033[32mCopying back\033[0m")
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

	with open('input/recipe-problems.tex', 'w+') as output:
		for problem in settings['problems']:
			output.write("\\addProblem{{{0}}}{{{1}}}{{{2}}}\n".format(problem['name'], problem['pointsDescription'], problem['pointsCode']))

	with open('input/recipe-solutions.tex', 'w+') as output:
		for problem in settings['problems']:
			output.write("\\addSolution{{{0}}}{{{1}}}{{{2}}}{{{3}}}\n".format(problem['name'], problem['solutionBy'], problem['evaluationBy'], problem['genderSuffix']))




parser = argparse.ArgumentParser(
	description				= "Prepare DeGeŠ series from repository",
)
parser.add_argument('seminar', choices = ['fks', 'kms', 'ksp', 'ufo', 'prask', 'fx'])
parser.add_argument('volume', type = int)
parser.add_argument('part', choices = ['autumn', 'spring'])
parser.add_argument('series', type = int, choices = [1, 2, 3]) 
parser.add_argument('-c', '--clean', action = 'store_true', help = 'call \'make distclean\' first')
parser.add_argument('-y', '--copy', action = 'store_true', help = 'copy output back to the repository')
args = parser.parse_args()
root = 'source/{0}/{1}/{2}/{3}/'.format(args.seminar, args.volume, args.part, args.series)

if args.clean:
	clean()

init()
processJson()

if os.system('make') != 0:
	raise Exception("make did not return 0, aborting")

if args.copy:
	copyBack()
