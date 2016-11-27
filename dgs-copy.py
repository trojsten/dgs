#!/usr/bin/python3

import os, re, datetime, argparse, shutil, json, colorama
from colorama import Fore as cf

colorama.init()

VERSION = "1.00"
DATE = "2016-09-11"

parser = argparse.ArgumentParser(
    description             = "Prepare and compile a DeGeŠ round from repository",
)
parser.add_argument('seminar', choices = ['fks', 'kms', 'ksp', 'ufo', 'prask', 'fx'])
parser.add_argument('volume', type = int)
parser.add_argument('part', type = int, choices = [1, 2])
parser.add_argument('round', type = int, choices = [1, 2, 3]) 

args = parser.parse_args()

for problem in range(1, 8):
    query = "scp ./output/{seminar}/{volume}/{part}/{round}/{problem:02d}/problem.html ksp.sk:/var/www-archiv/trojstenweb/tasks/{Seminar}/{volume}rocnik/{pr}kolo/zadania/html/prikl{problem}.html".format(
        seminar = args.seminar,
        volume = args.volume,
        part = args.part,
        round = args.round,
        problem = problem,
        Seminar = args.seminar.upper(),
        pr = (args.part - 1) * 3 + args.round
    )
    print(query)
    os.system(query)

for problem in range(1, 8):
    query = "scp ./output/{seminar}/{volume}/{part}/{round}/{problem:02d}/solution.html ksp.sk:/var/www-archiv/trojstenweb/tasks/{Seminar}/{volume}rocnik/{pr}kolo/vzoraky/html/prikl{problem}.html".format(
        seminar = args.seminar,
        volume = args.volume,
        part = args.part,
        round = args.round,
        problem = problem,
        Seminar = args.seminar.upper(),
        pr = (args.part - 1) * 3 + args.round
    )   
    print(query)
    os.system(query)

query = "scp ./output/{seminar}/{volume}/{part}/{round}/problems.pdf ksp.sk:/var/www-archiv/trojstenweb/tasks/{Seminar}/{volume}rocnik/{pr}kolo/zadania/zadania.pdf".format(
    seminar = args.seminar,
    volume = args.volume,
    part = args.part,
    round = args.round,
    Seminar = args.seminar.upper(),
    pr = (args.part - 1) * 3 + args.round
)
print(query)
os.system(query)

query = "scp ./output/{seminar}/{volume}/{part}/{round}/solutions.pdf ksp.sk:/var/www-archiv/trojstenweb/tasks/{Seminar}/{volume}rocnik/{pr}kolo/vzoraky/vzoraky.pdf".format(
    seminar = args.seminar,
    volume = args.volume,
    part = args.part,
    round = args.round,
    Seminar = args.seminar.upper(),
    pr = (args.part - 1) * 3 + args.round
)
print(query)
os.system(query)

query = "find ./source/{seminar}/{volume}/{part}/{round}/ \( -name '*.jpg' -o -name '*.png' \) -exec scp '{{}}' ksp.sk:/var/www-archiv/trojstenweb/tasks/{Seminar}/{volume}rocnik/{pr}kolo/obrazky/ \;".format(
    seminar = args.seminar,
    volume = args.volume,
    part = args.part,
    round = args.round,
    Seminar = args.seminar.upper(),
    pr = (args.part - 1) * 3 + args.round
)
print(query)
os.system(query)


