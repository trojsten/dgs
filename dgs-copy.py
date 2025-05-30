#!/usr/bin/env python

import os
import argparse

from typing import Tuple


VERSION = "4.0"
DATE = "2024-11-23"


def fire(query):
    print(query)
    return os.system(query)


def problem_count(seminar: str, volume: int) -> Tuple[str, int]:
    sr = seminar
    if seminar == 'FKS':
        if volume < 38:
            (sr, count) = ('FKS-old', 7)
        else:
            (sr, count) = ('FKS', 8)
    elif seminar == 'FX':
        count = 6
    else:
        raise ValueError(f"Unsupported combination {seminar}/{volume}")

    return sr, count


COPY_EXTENSIONS = ['jpg', 'svg', 'png', 'kmz', 'py']


def main():
    parser = argparse.ArgumentParser(description="Copy a DeGeŠ round to www-archiv")
    parser.add_argument('seminar', choices=['FKS', 'KMS', 'KSP', 'UFO', 'PRASK', 'FX', 'Suši'])
    parser.add_argument('volume', type=int)
    parser.add_argument('part', type=int, choices=[1, 2])
    parser.add_argument('round', choices=['1', '2', '3', 'outdoor'])
    parser.add_argument('-d', '--dry-run', action='store_true')

    args = parser.parse_args()

    # SuŠi hack
    issue = 100 if args.round == 'outdoor' else int(args.round)

    # FKS hack: volumes <= 37 are now marked as "FKS-old"
    seminar_remote, count = problem_count(args.seminar, args.volume)

    path_fragment_local = f"{args.seminar}/{args.volume:02d}/{args.part}/{issue}"
    path_fragment_remote = f"{seminar_remote}/{args.volume}/{args.part}/{issue}"

    # delete the temporary directory if present
    os.system("rm -rf tasks")

    # copy HTML files
    for local, remote in (('problem', 'zadania'), ('solution', 'vzoraky')):
        for problem in range(1, count + 1):
            pfl = f"{path_fragment_local}/{problem:02d}"
            fire(f"mkdir -p tasks/{path_fragment_remote}/{remote}/html && "
                 f"ln -s $(pwd)/output/seminar/{pfl}/{local}.html "
                 f"tasks/{path_fragment_remote}/{remote}/html/prikl{problem}.html")

    # copy pdf files
    fire(f"ln -s $(pwd)/output/seminar/{path_fragment_local}/problems.pdf "
         f"tasks/{path_fragment_remote}/zadania/zadania.pdf")
    fire(f"ln -s $(pwd)/output/seminar/{path_fragment_local}/solutions.pdf "
         f"tasks/{path_fragment_remote}/vzoraky/vzoraky.pdf")

    # copy pictures
    copy_wildcard = ' -o '.join([f"-name '*.{x}'" for x in COPY_EXTENSIONS])

    # stupid hack to make it work with trojstenweb
    fire(rf"mkdir -p tasks/{path_fragment_remote}/obrazky/ && "
         rf"find output/seminar/{path_fragment_local}/ \( {copy_wildcard} \) "
         rf"-exec ln -s $(pwd)/'{{}}' tasks/{path_fragment_remote}/obrazky/ \;")

    # rsync everything to server
    if not args.dry_run:
        fire(f"rsync --recursive --compress --verbose --partial --progress --copy-links --chmod=775 "
             f"tasks trojstenweb@ksp:/var/www/trojstenweb/")

    # delete the temporary structure
    fire("rm -rf tasks")


main()
