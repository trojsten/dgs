"""
The numbers a volume never showed anywhere: who wrote what, which tags exist, what is translated.

Counting only -- nothing here judges. A blank author column across volumes 19 to 24 is a fact, and
the fact is the point.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass, field

ROLES = ('idea', 'problem', 'solution')


@dataclass
class Stats:
    problems: int = 0
    metas_present: int = 0
    #: person -> role -> count
    authors: dict = field(default_factory=lambda: defaultdict(Counter))
    authors_missing: int = 0
    tags: Counter = field(default_factory=Counter)
    untagged: int = 0
    #: language -> file name -> count
    languages: dict = field(default_factory=lambda: defaultdict(Counter))
    #: files that sit beside the unit rather than in a language directory -- `answer.md` and the
    #: like. Kept apart from `languages` so a language count stays a count of languages.
    shared: Counter = field(default_factory=Counter)
    #: how many problems carry each templating block, and how many entries in total
    templating: dict = field(default_factory=lambda: defaultdict(int))

    @property
    def people(self):
        """Authors by total contributions, most first."""
        return sorted(self.authors.items(), key=lambda kv: (-sum(kv[1].values()), kv[0]))

    @property
    def language_list(self):
        return sorted(self.languages)

    @property
    def file_kinds(self):
        return sorted({name for counts in self.languages.values() for name in counts})

    @property
    def shared_kinds(self):
        return sorted(self.shared)


def collect(sources) -> Stats:
    stats = Stats()
    for unit in sources.unit_list:
        stats.problems += 1
        if unit.meta is not None:
            stats.metas_present += 1
        meta = unit.meta or {}

        # `authors_missing` counts a problem that *has* the block and records nobody in it. A meta
        # with no `authors` key at all is a different thing -- scholar and seminar do not use one --
        # and a problem with no meta is counted by `metas_present`. One number, one meaning.
        authors = meta.get('authors')
        if isinstance(authors, dict):
            named = False
            for role in ROLES:
                for person in authors.get(role) or []:
                    # `?` means "not recorded", so it is not a person and must not appear in a
                    # leaderboard as though it were one
                    if str(person).strip() == '?':
                        continue
                    stats.authors[str(person)][role] += 1
                    named = True
            if not named:
                stats.authors_missing += 1
        elif isinstance(authors, list):          # the old flat form, before the roles existed
            for person in authors:
                stats.authors[str(person)]['idea'] += 1
            if not authors:
                stats.authors_missing += 1

        tags = meta.get('tags') or []
        stats.tags.update(tags)
        if not tags:
            stats.untagged += 1

        for block in ('values', 'derived', 'eq'):
            entries = meta.get(block) or {}
            if entries:
                stats.templating[block] += 1
                stats.templating[f'{block}_entries'] += len(entries)

        for lang, files in unit.translated.items():
            stats.languages[lang].update(files.keys())
        stats.shared.update(unit.shared.keys())
    return stats
