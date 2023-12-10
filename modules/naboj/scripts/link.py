#!/usr/bin/env python

import argparse
import argparsedirs
import subprocess
import os
import sys
import glob

from pathlib import Path

sys.path.append('.')

from core import i18n


class Linker:
    """ Links missing translations to another language """

    def __init__(self):
        self.argparser = argparse.ArgumentParser()
        self.argparser.add_argument('root', action=argparsedirs.ReadableDir)
        self.argparser.add_argument('competition', type=str)
        self.argparser.add_argument('volume', type=int)
        self.argparser.add_argument('from_lang', type=str, choices=i18n.languages.keys())
        self.argparser.add_argument('to_lang', type=str, choices=i18n.languages.keys())
        self.argparser.add_argument('--problems', action='store_true')
        self.argparser.add_argument('--solutions', action='store_true')
        self.argparser.add_argument('--answer-extra', action='store_true')
        self.argparser.add_argument('--dry-run', action='store_true')
        self.args = self.argparser.parse_args()

        self.root = Path(self.args.root)
        self.path = self.root / self.args.competition / f"{self.args.volume:02d}" / "problems"

    def link(self):
        files = glob.glob(f"**/{self.args.from_lang}/problem.md", root_dir=self.path, recursive=True)

        for f in files:
            problem_id, _, filename = tuple(f.split('/'))

            if self.args.problems:
                self.call_ln(problem_id, 'problem.md')

            if self.args.solutions:
                self.call_ln(problem_id, 'solution.md')

            if self.args.answer_extra:
                self.call_ln(problem_id, 'answer-extra.md')

    def call_ln(self, problem_id, filename):
        self.ln(self.path / problem_id / self.args.from_lang, filename,
                Path("..") / self.args.to_lang / filename)

    def ln(self, cwd, file, relative_target):
        if self.args.dry_run:
            print(f"Would run cd {cwd}, then ln -s {relative_target} {file}")
        else:
            try:
                subprocess.run(["ln", "-s", relative_target, file], cwd=cwd, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Failed to create {relative_target} in {cwd}")
                pass

os.chdir('.')
Linker().link()

