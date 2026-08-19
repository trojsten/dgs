"""What an audit is made of: a scope to look at, and the findings that come back."""
from dataclasses import dataclass, field


#: Severities, most serious first. `error` means the build breaks or the page comes out wrong;
#: `warning` means something is inconsistent and a person has to decide; `info` records a thing
#: that is deliberate, so that nobody spends an afternoon rediscovering it.
SEVERITIES = ('error', 'warning', 'info')


@dataclass(frozen=True, slots=True)
class Finding:
    """One thing a check noticed, at one place."""
    check: str                      # stable id, e.g. 'label-schema'
    severity: str
    message: str
    unit: str | None = None         # unit path relative to the module root, None if scope-wide
    where: str = ''                 # language, file name or line, whatever the check can say
    line: int | None = None

    def __post_init__(self):
        if self.severity not in SEVERITIES:
            raise ValueError(f"Unknown severity {self.severity!r}")

    @property
    def unit_name(self):
        """The last path segment -- the problem id, which is what a table wants to show."""
        return self.unit.rsplit('/', 1)[-1] if self.unit else ''


@dataclass(frozen=True, slots=True)
class Check:
    """A registered check: what it is called, how bad it is, and the function that runs it."""
    id: str
    severity: str
    title: str
    run: object                     # (Sources) -> Iterable[Finding]
    modules: tuple = ()             # module names it applies to; empty means all of them


REGISTRY: dict[str, Check] = {}


def check(check_id, severity, title, *, modules=()):
    """
    Register a source-only check.

    The function receives the scope's `Sources` and yields `Finding`s. It must not write anything
    and must not shell out -- everything at this level is a file read and a regex, which is why a
    pass over the whole repository costs a fifth of a second.
    """
    def register(fn):
        if check_id in REGISTRY:
            raise ValueError(f"Duplicate check id {check_id!r}")
        REGISTRY[check_id] = Check(id=check_id, severity=severity, title=title,
                                   run=fn, modules=tuple(modules))
        return fn
    return register


def applicable(module: str):
    """The checks that apply to a module, in registration order."""
    return [c for c in REGISTRY.values() if not c.modules or module in c.modules]
