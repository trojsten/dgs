#!/usr/bin/env python

import yaml
import argparse
import sys


class TeamProcessor():
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="DeGeŠ Náboj team processor",
        )
        self.parser.add_argument('infile', type=argparse.FileType('r'), default=sys.stdin)
        self.parser.add_argument('outfile', nargs='?', type=argparse.FileType('w'), default=sys.stdout)
        self.parser.add_argument('-v', '--verbose', action='store_true')
        self.parser.add_argument('-w', '--warnings', action='store_true')
        self.parser.add_argument('language', type=str)
        self.args = self.parser.parse_args()

    def process(self):
        data = yaml.safe_load(self.args.infile)

        for team in data['teams']:
            team['language'] = self.args.language
        yaml.dump(data, self.args.outfile, default_flow_style=False)
        print(f"A total of {len(data['teams'])} teams")


TeamProcessor().process()
