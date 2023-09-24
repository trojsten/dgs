#!/usr/bin/env python

import argparse
import os
from pathlib import Path

import argparsedirs


def fire(query):
    print(query)
    os.system(query)


class PictureLinker():
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('root', action=argparsedirs.ReadableDir)
        parser.add_argument('competition', type=str, choices=['math', 'phys', 'chem', 'junior'])
        parser.add_argument('volume', type=int)
        parser.add_argument('master', type=str, choices=['sk'])
        parser.add_argument('slave', type=str, choices=['en', 'cs', 'pl', 'hu', 'ru', 'fa', 'es'])
        self.args = parser.parse_args()
        self.root = Path(self.args.root)
        self.competition = self.args.competition
        self.volume = f"{self.args.volume:02d}"

        if self.args.master == self.args.slave:
            raise ValueError(f"Slave must be different from master")

    def link(self):
        master_path = self.root / self.competition / self.volume / 'languages' / self.args.master
        slave_path = self.root / self.competition / self.volume / 'languages' / self.args.slave
        print(f"Deleting symlinks in {slave_path}")
        fire(
            f'cd {slave_path} &&' \
            f'find . -name "*.svg" -type "l" -delete; '
        )
        print(f"Creating new symlinks from {slave_path} to {master_path}")
        fire(
            f"cd {master_path} && " \
            f'find . -name "*.svg" -exec ln -s -T ../../{self.args.master}/{{}} ../{self.args.slave}/{{}} \\;'
        )


PictureLinker().link()
