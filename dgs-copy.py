#!/usr/bin/env python3

import os
import argparse


VERSION = "3.01"
DATE = "2022-10-09"


def fire(query):
    print(query)
    return os.system(query)


def main():
    parser = argparse.ArgumentParser(description="Copy a DeGeŠ round to www-archiv")
    parser.add_argument('seminar', choices=['FKS', 'KMS', 'KSP', 'UFO', 'PRASK', 'FX', 'Suši'])
    parser.add_argument('volume', type=int)
    parser.add_argument('part', type=int, choices=[1, 2])
    parser.add_argument('round', choices=['1', '2', '3', 'outdoor'])
    parser.add_argument('user', type=str)
    parser.add_argument('-d', '--dry-run', action='store_true')

    args = parser.parse_args()

    # SuŠi hack
    round = 100 if args.round == 'outdoor' else int(args.round)

    # FKS hack: volumes <= 37 are now marked as "FKS-old"
    if args.seminar == 'FKS' and args.volume <= 37:
        remote_seminar = "FKS-old"
        count = 7
    else:
        remote_seminar = args.seminar
        count = 8

    path_fragment_local = f"{args.seminar}/{args.volume:02d}/{args.part}/{round}"
    path_fragment_remote = f"{remote_seminar}/{args.volume}/{args.part}/{round}"

    # delete the temporary directory
    os.system("rm -rf tasks")

    # copy HTML files
    for local, remote in (('problem', 'zadania'), ('solution', 'vzoraky')):
        for problem in range(1, count + 1):
            pfl = f"{path_fragment_local}/{problem:02d}"
            fire(f"mkdir -p tasks/{path_fragment_remote}/{remote}/html && " \
                f"ln -s $(pwd)/output/seminar/{pfl}/{local}.html " \
                f"tasks/{path_fragment_remote}/{remote}/html/prikl{problem}.html")

    # copy pdf files
    fire(f"ln -s $(pwd)/output/seminar/{path_fragment_local}/problems.pdf tasks/{path_fragment_remote}/zadania/zadania.pdf")
    fire(f"ln -s $(pwd)/output/seminar/{path_fragment_local}/solutions.pdf tasks/{path_fragment_remote}/vzoraky/vzoraky.pdf")

    # copy pictures
    fire(rf"mkdir -p tasks/{path_fragment_remote}/obrazky/ && " \
        rf"find output/seminar/{path_fragment_local}/ \( -name '*.jpg' -o -name '*.png' -o -name '*.kmz' \) " \
        rf"-exec ln -s $(pwd)/'{{}}' tasks/{path_fragment_remote}/obrazky/ \;")

    # rsync everything to server and delete
    if not args.dry_run:
        fire(f"rsync --recursive --compress --verbose --partial --progress --copy-links --chmod=775 tasks {args.user}@ksp.sk:/var/www-archiv/trojstenweb")

    fire("rm -rf tasks")


main()
