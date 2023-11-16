import argparse
import argparsedirs
import subprocess

from pathlib import Path

import core.utilities.schema as sch


class Linker:
    def __init__(self):
        self.argparser = argparse.ArgumentParser()
        self.argparser.add_argument('root', type=argparsedirs.ReadableDir)
        self.argparser.add_argument('competition', type=str)
        self.argparser.add_argument('volume', type=int)
        self.argparser.add_argument('from', type=sch.valid_language)
        self.argparser.add_argument('to', type=sch.valid_language)
        self.argparser.add_argument('--problems', action='store_true')
        self.argparser.add_argument('--solutions', action='store_true')
        self.argparser.add_argument('--answer-extra', action='store_true')
        self.args = self.argparser.parse_args()

        self.path = self.root / self.args.competition / f"{self.args.volume:02d}"

    def link(self):
        files = glob.glob()
        subprocess.run(["ln -s {}"])