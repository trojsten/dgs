import itertools

from schema import Schema, Optional, Regex, Or

import core.utilities.globals as glob
from core.builder.validator import FileSystemValidator
from core.utilities.schema import valid_language
import core.utilities.colour as c


file = 'file'
link = 'link'
file_or_link = Or(file, link)


class NabojValidator(FileSystemValidator):
    _schema = Schema({
        'problems': {
            str: {
                valid_language: {
                    Optional('problem.md'): file_or_link,
                    Optional('solution.md'): file_or_link,
                    Optional('answer-extra.md'): file_or_link,
                },
                'answer.md': file,
                Optional('answer-interval.md'): file,
                Optional('meta.yaml'): file,
                Optional(Regex(r'[\w-]+\.(png|svg|gp|py|dat)')): file,
            },
        },
        'languages': {
            valid_language: {
                'meta.yaml': file,
                'intro.jtt': file_or_link,
                'instructions-inner.jtt': file_or_link,
                'evaluators.jtt': file_or_link,
            }
        },
        'venues': {
            Regex(r'\w+'): {
                'instructions-inner.jtt': file_or_link,
                'evaluators.jtt': link,
                'meta.yaml': file,
            },
        },
        'meta.yaml': file,
    })

    def __init__(self, *path):
        super().__init__(*path)
        self.debug = False

    def perform_extra_checks(self):
        self._check_same_translations()
        self._check_presence('problem.md')
        self._check_presence('solution.md')
        self._check_presence('answer-extra.md', optional=True)

    @staticmethod
    def _colour(what):
        return {
            None: c.err,
            file: c.ok,
            link: c.path,
        }[what]

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

    def _check_presence(self, filename, *, optional: bool = False):
        for problem_id, problem in sorted(self.tree['problems'].items()):
            translations = [x for x in problem.keys() if x in glob.languages.keys()]
            is_present = {
                trans: problem[trans][filename] if filename in problem[trans] else None for trans in translations
            }

            lp = len([x for x, y in is_present.items() if y])
            # If there are all files present, we're good, and if this is an optional file, then also if none are present
            ok = (lp == len(translations)) or (optional and lp == 0)
            if self.debug or not ok:
                print(f"Warning for problem {c.name(problem_id):<30}: "
                      f"{'Either all or none ' if optional else 'All '}"
                      f"of the translations should contain file {c.path(filename)}, "
                      f"but found {' '.join([self._colour(kind)(lang) for lang, kind in is_present.items()])}")
