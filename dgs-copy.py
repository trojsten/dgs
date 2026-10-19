#!/usr/bin/env python

import argparse
import os

VERSION = "5.0"
DATE = "2025-11-18"


def fire(query):
    print(query)
    return os.system(query)


def problem_count(seminar: str, volume: int) -> tuple[str, int]:
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


def main():
    """
    Copy a round's PDFs to the archive.

    It used to carry the HTML too, and a flat `obrazky/` directory of every picture in the round
    symlinked together -- a layout the old website wanted and nothing else did. That layout had
    reached back into the convertor, which rewrote every `<img src=>` to sit under `obrazky/` and
    *failed the build* on any that did not, so a TikZ picture could not be part of an HTML page
    at all. Both are gone, and the HTML is now a thing this repository renders for itself rather
    than an export shaped by one consumer.
    """
    parser = argparse.ArgumentParser(description="Copy a DeGeŠ round's PDFs to www-archiv")
    parser.add_argument('seminar', choices=['FKS', 'KMS', 'KSP', 'UFO', 'PRASK', 'FX', 'Suši'])
    parser.add_argument('volume', type=int)
    parser.add_argument('part', type=int, choices=[1, 2])
    parser.add_argument('round', choices=['1', '2', '3', 'outdoor'])
    parser.add_argument('-d', '--dry-run', action='store_true')

    args = parser.parse_args()

    # SuŠi hack
    issue = 100 if args.round == 'outdoor' else int(args.round)

    # FKS hack: volumes <= 37 are now marked as "FKS-old"
    # the count was the HTML loop's; what is left of this function is the remote name,
    # which still has to know that FKS up to volume 37 is published as `FKS-old`
    seminar_remote, _ = problem_count(args.seminar, args.volume)

    path_fragment_local = f"{args.seminar}/{args.volume:02d}/{args.part}/{issue}"
    path_fragment_remote = f"{seminar_remote}/{args.volume}/{args.part}/{issue}"

    # delete the temporary directory if present
    os.system("rm -rf tasks")

    # copy pdf files
    fire(f"ln -s $(pwd)/output/seminar/{path_fragment_local}/problems.pdf "
         f"tasks/{path_fragment_remote}/zadania/zadania.pdf")
    fire(f"ln -s $(pwd)/output/seminar/{path_fragment_local}/solutions.pdf "
         f"tasks/{path_fragment_remote}/vzoraky/vzoraky.pdf")

    # rsync everything to server
    if not args.dry_run:
        fire("rsync --recursive --compress --verbose --partial --progress --copy-links --chmod=775 "
             "tasks trojstenweb@ksp:/var/www/trojstenweb/")

    # delete the temporary structure
    fire("rm -rf tasks")


main()
