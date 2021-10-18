#!/usr/bin/env python3

import os, re, datetime, argparse, shutil, json, colorama
from colorama import Fore as cf

colorama.init()

VERSION = "2.00"
DATE = "2021-10-18"

parser = argparse.ArgumentParser(description="Copy a DeGeŠ round to www-archiv")
parser.add_argument('seminar', choices=['FKS', 'KMS', 'KSP', 'UFO', 'PRASK', 'FX', 'Suši'])
parser.add_argument('volume', type=int)
parser.add_argument('part', type=int, choices=[1, 2])
parser.add_argument('round', choices=['1', '2', '3', 'outdoor'])
parser.add_argument('user')

args = parser.parse_args()

seminar = args.seminar
volume = args.volume
part = args.part
round = 100 if args.round == 'outdoor' else int(args.round)

path_fragment_local = f"{seminar}/{volume:02d}/{part}/{round}"
path_fragment_remote = f"{seminar}/{volume}/{part}/{round}"

def fire(query):
    print(query)
    return os.system(query)


# Delete the temporary directory
os.system("rm -rf tasks")

for problem in range(1, 8):
    path = f"{path_fragment_local}/{problem:02d}"
    fire(f"mkdir -p tasks/{path_fragment_remote}/zadania/html && " \
        f"ln -s $(pwd)/output/seminar/{path}/problem.html " \
        f"tasks/{path_fragment_remote}/zadania/html/prikl{problem}.html")

for problem in range(1, 8):
    path = f"{path_fragment_local}/{problem:02d}"
    fire(f"mkdir -p tasks/{path_fragment_remote}/vzoraky/html && " \
        f"ln -s $(pwd)/output/seminar/{path}/solution.html " \
        f"tasks/{path_fragment_remote}/vzoraky/html/prikl{problem}.html")

fire(f"ln -s $(pwd)/output/seminar/{path_fragment_local}/problems.pdf tasks/{path_fragment_remote}/zadania/zadania.pdf")
fire(f"ln -s $(pwd)/output/seminar/{path_fragment_local}/solutions.pdf tasks/{path_fragment_remote}/vzoraky/vzoraky.pdf")
fire(f"mkdir -p tasks/{path_fragment_remote}/obrazky/ && " \
    f"find output/seminar/{path_fragment_local}/ \( -name '*.jpg' -o -name '*.png' -o -name '*.kmz' \) " \
    f"-exec ln -s $(pwd)/'{{}}' tasks/{path_fragment_remote}/obrazky/ \;")

fire(f"rsync -rzvhPL tasks {args.user}@ksp.sk:/var/www-archiv/trojstenweb && rm -rf tasks")
