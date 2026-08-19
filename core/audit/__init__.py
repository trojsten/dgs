"""
Static audit of a scope -- a volume, a seminar year, whatever a module groups its problems by.

Two layers. This one is source-only: it reads every file once and runs a registry of checks over
the result, which costs about a fifth of a second for the whole repository, so nothing needs to be
cached or made incremental. `core.audit.build` is the other one, and it shells out to make.

    from core.audit import audit
    report = audit(Path('source/naboj'), 'naboj', 'phys/28', units)
    report.findings, report.stats
"""
from dataclasses import dataclass, field
from pathlib import Path

from core.audit import checks                      # noqa: F401  -- populates the registry
from core.audit.model import REGISTRY, SEVERITIES, Check, Finding, applicable
from core.audit.sources import Sources, read_scope
from core.audit.stats import Stats, collect
from core.audit.status import STATES, Status, statuses, worst


@dataclass
class Report:
    scope: str
    module: str
    findings: list = field(default_factory=list)
    stats: Stats = None
    sources: Sources = None
    #: unit path -> kind -> Status. "How far along is this", as against the findings' "what is
    #: wrong with this": a column wants a verdict per problem, not a list of defects.
    statuses: dict = field(default_factory=dict)

    def by_unit(self):
        """Findings grouped by unit path; scope-wide ones under the empty string."""
        out = {}
        for f in self.findings:
            out.setdefault(f.unit or '', []).append(f)
        return out

    def by_check(self):
        counts = {}
        for f in self.findings:
            counts[f.check] = counts.get(f.check, 0) + 1
        return counts

    def by_severity(self):
        counts = {s: 0 for s in SEVERITIES}
        for f in self.findings:
            counts[f.severity] += 1
        return counts

    def status_summary(self):
        """Per kind, how many problems are in each state, and the worst state overall."""
        out = {}
        for kinds in self.statuses.values():
            for kind, status in kinds.items():
                bucket = out.setdefault(kind, {s: 0 for s in STATES})
                bucket[status.state] += 1
        return {kind: {'counts': counts,
                       'worst': worst([s for s, n in counts.items() if n])}
                for kind, counts in out.items()}


def audit(module_root: Path, module: str, scope: str, unit_paths) -> Report:
    sources = read_scope(module_root, module, scope, unit_paths)
    findings = []
    for c in applicable(module):
        for finding in c.run(sources):
            # a problem may opt out of a check whose finding is the point of the problem
            unit = sources.units.get(finding.unit) if finding.unit else None
            if unit is not None and checks.ignored(unit, finding.check):
                continue
            findings.append(finding)
    findings.sort(key=lambda f: (SEVERITIES.index(f.severity), f.unit or '', f.check))
    return Report(scope=scope, module=module, findings=findings,
                  stats=collect(sources), sources=sources,
                  statuses=statuses(sources))
