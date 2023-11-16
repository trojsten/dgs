import pprint
import _io
import itertools
from schema import Schema, Optional, Regex

import core.utilities.globals as glob
from core.builder.validator import FileSystemValidator
from core.utilities.schema import valid_language
import core.utilities.colour as c


file = _io.TextIOWrapper



class NabojValidator(FileSystemValidator):
    _schema = Schema({
        'problems': {
            str: {
                valid_language: {
                    Optional('problem.md'): file,
                    Optional('solution.md'): file,
                    Optional('answer-extra.md'): file,
                },
                'answer.md': file,
                Optional('answer-interval.md'): file,
                Optional('meta.yaml'): file,
                Optional(Regex(r'[a-z0-9-]+\.(png|svg|gp|py|dat)')): file,
            },
        },
        'languages': {
            valid_language: {
                'meta.yaml': file,
                'intro.jtt': file,
                'instructions-inner.jtt': file,
                'evaluators.jtt': file,
            }
        },
        'venues': {
            Regex(r'[a-z]+'): {
                'instructions-inner.jtt': file,
                'evaluators.jtt': file,
                'meta.yaml': file,
            },
        },
        'meta.yaml': file,
    })

    def perform_extra_checks(self):
        self._check_same_translations()
        self._check_answers_extra()

    def _check_same_translations(self) -> bool:
        if not self.tree['problems']:
            return True
        else:
            for (pid1, problem1), (pid2, problem2) in itertools.pairwise(self.tree['problems'].items()):
                translations1 = [x for x in problem1.keys() if x in glob.languages.keys()]
                translations2 = [x for x in problem2.keys() if x in glob.languages.keys()]
                if translations1 != translations2:
                    print(f"Warning: problem {pid1} has translations {translations1} "
                          f"and {pid2} has translations {translations2}")

    def _check_answers_extra(self):
        for problem_id, problem in self.tree['problems'].items():
            translations = [x for x in problem.keys() if x in glob.languages.keys()]
            has_extra = {trans: ('answer-extra.md' in problem[trans]) for trans in translations}
            if 0 < len([x for x, y in has_extra.items() if y]) < len(translations):
                print(f"Warning for problem {c.name(problem_id)}: "
                      f"Either all or none of the translations should contain {c.path('answer-extra.md')}, "
                      f"currently {' '.join([c.colour_boolean(x, y) for x, y in has_extra.items()])}")

