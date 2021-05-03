#!/usr/bin/env python3

import os, re, datetime, argparse, shutil, json, colorama
from colorama import Fore as cf

colorama.init()

VERSION = "2.00"
DATE = "2018-10-16"

parser = argparse.ArgumentParser(
    description             = "Copy a DeGeŠ round to www-archiv",
)
parser.add_argument('seminar', choices = ['FKS', 'KMS', 'KSP', 'UFO', 'PRASK', 'FX', 'SUSI'])
parser.add_argument('volume', type = int)
parser.add_argument('part', type = int, choices = [1, 2])
parser.add_argument('round', choices = ['1', '2', '3', 'outdoor'])
parser.add_argument('user')

args = parser.parse_args()

seminar2 = 'Suši' if args.seminar == 'SUSI' else args.seminar


query = "ssh {user}@ksp.sk 'rm -rf \
/var/www-archiv/trojstenweb/tasks/{seminar}/{volume}/{part}/{round} && mkdir -p \
/var/www-archiv/trojstenweb/tasks/{seminar}/{volume}/{part}/{round}/zadania/html/ \
/var/www-archiv/trojstenweb/tasks/{seminar}/{volume}/{part}/{round}/vzoraky/html/ \
/var/www-archiv/trojstenweb/tasks/{seminar}/{volume}/{part}/{round}/obrazky/'".format(
    seminar = seminar2,
    volume = args.volume,
    part = args.part,
    round = 100 if args.round == 'outdoor' else args.round,
    user = args.user,
)
print(query)
#os.system(query)

for problem in range(1, 8):
    query = "mkdir -p tasks/{seminar2}/{volume}/{part}/{round2}/zadania/html && ln -s $(pwd)/output/seminar/{seminar1}/{volume:02d}/{part}/{round1}/{problem:02d}/problem.html tasks/{seminar2}/{volume}/{part}/{round2}/zadania/html/prikl{problem}.html".format(
        seminar1 = args.seminar,
        seminar2 = seminar2,
        volume = args.volume,
        part = args.part,
        round1 = args.round,
        round2 = 100 if args.round == 'outdoor' else args.round,
        problem = problem,
        user = args.user,
    )
    print(query)
    os.system(query)

for problem in range(1, 8):
    query = "mkdir -p tasks/{seminar2}/{volume}/{part}/{round2}/vzoraky/html && ln -s $(pwd)/output/seminar/{seminar1}/{volume:02d}/{part}/{round1}/{problem:02d}/solution.html tasks/{seminar2}/{volume}/{part}/{round2}/vzoraky/html/prikl{problem}.html".format(
        seminar1 = args.seminar,
        seminar2 = seminar2,
        volume = args.volume,
        part = args.part,
        round1 = args.round,
        round2 = 100 if args.round == 'outdoor' else args.round,
        problem = problem,
        user = args.user,
    )
    print(query)
    os.system(query)

query = "ln -s $(pwd)/output/seminar/{seminar1}/{volume:02d}/{part}/{round1}/problems.pdf tasks/{seminar2}/{volume}/{part}/{round2}/zadania/zadania.pdf".format(
    seminar1 = args.seminar,
    seminar2 = seminar2,
    volume = args.volume,
    part = args.part,
    round1 = args.round,
    round2 = 100 if args.round == 'outdoor' else args.round,
    user = args.user,
)
print(query)
os.system(query)

query = "ln -s $(pwd)/output/seminar/{seminar1}/{volume:02d}/{part}/{round1}/solutions.pdf tasks/{seminar2}/{volume}/{part}/{round2}/vzoraky/vzoraky.pdf".format(
    seminar1 = args.seminar,
    seminar2 = seminar2,
    volume = args.volume,
    part = args.part,
    round1 = args.round,
    round2 = 100 if args.round == 'outdoor' else args.round,
    user = args.user,
)
print(query)
os.system(query)

query = "mkdir -p tasks/{seminar2}/{volume}/{part}/{round2}/obrazky/ && find output/seminar/{seminar1}/{volume:02d}/{part}/{round1}/ \( -name '*.jpg' -o -name '*.png' -o -name '*.kmz' \) -exec ln -s $(pwd)/'{{}}' tasks/{seminar2}/{volume}/{part}/{round2}/obrazky/ \;".format(
    seminar1 = args.seminar,
    seminar2 = seminar2,
    volume = args.volume,
    part = args.part,
    round1 = args.round,
    round2 = 100 if args.round == 'outdoor' else args.round,
    user = args.user,
)
print(query)
os.system(query)

query = "rsync -rzvhPL tasks {user}@ksp.sk:/var/www-archiv/trojstenweb && rm -rf tasks".format(
    user = args.user,
)
print(query)
os.system(query)
