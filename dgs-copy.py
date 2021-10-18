#!/usr/bin/env python3

import os, re, datetime, argparse, shutil, json, colorama
from colorama import Fore as cf


VERSION = "3.00"
DATE = "2021-10-18"


def fire(query):
    print(query)
    return os.system(query)


def main():
    colorama.init()

    parser = argparse.ArgumentParser(description="Copy a DeGeŠ round to www-archiv")
    parser.add_argument('seminar', choices=['FKS', 'KMS', 'KSP', 'UFO', 'PRASK', 'FX', 'Suši'])
    parser.add_argument('volume', type=int)
    parser.add_argument('part', type=int, choices=[1, 2])
    parser.add_argument('round', choices=['1', '2', '3', 'outdoor'])
    parser.add_argument('user', type=str)

    args = parser.parse_args()

    round = 100 if args.round == 'outdoor' else int(args.round)

    path_fragment_local = f"{args.seminar}/{args.volume:02d}/{args.part}/{round}"
    path_fragment_remote = f"{args.seminar}/{args.volume}/{args.part}/{round}"

    # Delete the temporary directory
    os.system("rm -rf tasks")

    # Copy HTML files
    for local, remote in (('problem', 'zadania'), ('solution', 'vzoraky')):
        for problem in range(1, 8):
            pfl = f"{path_fragment_local}/{problem:02d}"
            fire(f"mkdir -p tasks/{path_fragment_remote}/{remote}/html && " \
                f"ln -s $(pwd)/output/seminar/{pfl}/{local}.html " \
                f"tasks/{path_fragment_remote}/{remote}/html/prikl{problem}.html")

    # Copy pdf files
    fire(f"ln -s $(pwd)/output/seminar/{path_fragment_local}/problems.pdf tasks/{path_fragment_remote}/zadania/zadania.pdf")
    fire(f"ln -s $(pwd)/output/seminar/{path_fragment_local}/solutions.pdf tasks/{path_fragment_remote}/vzoraky/vzoraky.pdf")

    # Copy pictures
    fire(f"mkdir -p tasks/{path_fragment_remote}/obrazky/ && " \
        f"find output/seminar/{path_fragment_local}/ \( -name '*.jpg' -o -name '*.png' -o -name '*.kmz' \) " \
        f"-exec ln -s $(pwd)/'{{}}' tasks/{path_fragment_remote}/obrazky/ \;")

    # rsync everything to server and delete
    fire(f"rsync -rzvhPL tasks {args.user}@ksp.sk:/var/www-archiv/trojstenweb && rm -rf tasks")
