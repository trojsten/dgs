#!/usr/bin/env python3

import os, re, datetime, argparse, shutil, json, colorama
from colorama import Fore as cf

colorama.init()

VERSION = "2.00"
DATE = "2018-10-16"

parser = argparse.ArgumentParser(
    description             = "Copy a DeGeŠ round to www-archiv",
)
parser.add_argument('seminar', choices = ['FKS', 'KMS', 'KSP', 'UFO', 'PRASK', 'FX'])
parser.add_argument('volume', type = int)
parser.add_argument('part', type = int, choices = [1, 2])
parser.add_argument('round', type = int, choices = [1, 2, 3])
parser.add_argument('user')

args = parser.parse_args()

query = "ssh {user}@ksp.sk 'mkdir -p \
/var/www-archiv/trojstenweb/tasks/{seminar}/{volume}/{part}/{round}/zadania/html/ \
/var/www-archiv/trojstenweb/tasks/{seminar}/{volume}/{part}/{round}/vzoraky/html/ \
/var/www-archiv/trojstenweb/tasks/{seminar}/{volume}/{part}/{round}/obrazky/'".format(
    seminar = args.seminar,
    volume = args.volume,
    part = args.part,
    round = args.round,
    user = args.user,
)
print(query)
os.system(query)

for problem in range(1, 8):
    query = "scp ./output/seminar/{seminar}/{volume}/{part}/{round}/{problem:02d}/problem.html {user}@ksp.sk:/var/www-archiv/trojstenweb/tasks/{seminar}/{volume}/{part}/{round}/zadania/html/prikl{problem}.html".format(
        seminar = args.seminar,
        volume = args.volume,
        part = args.part,
        round = args.round,
        problem = problem,
        user = args.user,
    )
    print(query)
    os.system(query)

for problem in range(1, 8):
    query = "scp ./output/seminar/{seminar}/{volume}/{part}/{round}/{problem:02d}/solution.html {user}@ksp.sk:/var/www-archiv/trojstenweb/tasks/{seminar}/{volume}/{part}/{round}/vzoraky/html/prikl{problem}.html".format(
        seminar = args.seminar,
        volume = args.volume,
        part = args.part,
        round = args.round,
        problem = problem,
        user = args.user,
    )
    print(query)
    os.system(query)

query = "scp ./output/seminar/{seminar}/{volume}/{part}/{round}/problems.pdf {user}@ksp.sk:/var/www-archiv/trojstenweb/tasks/{seminar}/{volume}/{part}/{round}/zadania/zadania.pdf".format(
    seminar = args.seminar,
    volume = args.volume,
    part = args.part,
    round = args.round,
    user = args.user,
)
print(query)
os.system(query)

query = "scp ./output/seminar/{seminar}/{volume}/{part}/{round}/solutions.pdf {user}@ksp.sk:/var/www-archiv/trojstenweb/tasks/{seminar}/{volume}/{part}/{round}/vzoraky/vzoraky.pdf".format(
    seminar = args.seminar,
    volume = args.volume,
    part = args.part,
    round = args.round,
    user = args.user,
)
print(query)
os.system(query)

query = "find ./output/seminar/{seminar}/{volume}/{part}/{round}/ \( -name '*.jpg' -o -name '*.png' \) -exec scp '{{}}' {user}@ksp.sk:/var/www-archiv/trojstenweb/tasks/{seminar}/{volume}/{part}/{round}/obrazky/ \;".format(
    seminar = args.seminar,
    volume = args.volume,
    part = args.part,
    round = args.round,
    user = args.user,
)
print(query)
os.system(query)
