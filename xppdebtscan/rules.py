"""Debt-scan rule set: compiled regex flags plus their metadata.

Every regex here was tuned against real method source in a live corpus
first (the TrudAX/XppTools open-source tooling suite); the false-positive
caveats are recorded inline so the next maintainer knows why a pattern is
shaped the way it is.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Severity ordering used by the heatmap (worst wins per cell).
SEVERITIES = ("high", "medium", "low")


@dataclass
class Flag:
    """One debt-scan rule: a compiled regex plus its metadata."""

    name: str
    category: str
    severity: str
    pattern: re.Pattern
    #: minimum distinct matching lines before the flag fires (used to
    #: separate "declares a container" from "container-heavy plumbing").
    min_hits: int = 1
    description: str = ""


def line_hits(pattern: re.Pattern, source: str) -> List[Tuple[int, str]]:
    """(1-based line number, stripped line) for every line matching."""
    hits: List[Tuple[int, str]] = []
    for i, line in enumerate(source.splitlines(), start=1):
        if pattern.search(line):
            hits.append((i, line.strip()[:200]))
    return hits


FLAGS: List[Flag] = [
    # -- direct SQL ---------------------------------------------------------
    Flag(
        name="select_forupdate",
        category="direct_sql",
        severity="medium",
        # single-line form is enough in practice; multi-line selects are
        # handled by the per-line scan matching the "forupdate" keyword on
        # the select line itself. Caveat: forupdate alone is legitimate
        # X++; it is flagged as medium because in a tooling/utility layer
        # it usually marks data-fixing scripts that bypass business logic.
        pattern=re.compile(r"\bselect\b.*\bforupdate\b", re.IGNORECASE),
        description="select ... forupdate (direct record update path)",
    ),
    Flag(
        name="raw_sql_statement",
        category="direct_sql",
        severity="high",
        # connection.createStatement() is the unambiguous raw-SQL door.
        pattern=re.compile(r"\.createStatement\s*\(", re.IGNORECASE),
        description="Connection.createStatement (raw SQL execution)",
    ),
    Flag(
        name="raw_sql_execute",
        category="direct_sql",
        severity="high",
        # Caveat: a bare executeQuery( would be majority-false-positive:
        # FormDataSource.executeQuery() is idiomatic form code (verified:
        # most hits in the tuning corpus are datasource refreshes). We
        # therefore require the statement-object idiom on the same line.
        pattern=re.compile(
            r"\bstatement\s*\.\s*execute(Query|Update)", re.IGNORECASE),
        description="Statement.executeQuery/executeUpdate (raw SQL)",
    ),
    # -- deprecated / legacy patterns ---------------------------------------
    Flag(
        name="container_heavy",
        category="legacy",
        severity="low",
        # Caveat: a single container declaration is ordinary X++ (conlen,
        # conpeek plumbing everywhere). Only container-heavy methods (3+
        # lines mentioning the type) suggest a data-contract smell worth a
        # SysOperation/data-contract refactor. Tuned: 1-hit threshold
        # flagged ~10% of all methods in the tuning corpus, which is noise.
        pattern=re.compile(r"\bcontainer\b|\bcon(?:peek|poke|ins|del)\s*\(",
                           re.IGNORECASE),
        min_hits=3,
        description="container-heavy method (3+ container lines)",
    ),
    Flag(
        name="infolog_direct",
        category="legacy",
        severity="low",
        pattern=re.compile(r"\binfolog\s*\.", re.IGNORECASE),
        description="direct infolog.* call (prefer info()/warning()/error())",
    ),
    Flag(
        name="hardcoded_error_literal",
        category="localization",
        severity="medium",
        # Fires on throw error("...") / throw error(strFmt("...")) where the
        # literal starts with a letter, i.e. NOT a label reference ("@SYS...").
        # Caveat: intentionally does not chase literals passed via variables.
        pattern=re.compile(
            r"throw\s+error\s*\(\s*(?:strFmt\s*\(\s*)?\"[A-Za-z]"),
        description='throw error("English literal") (localization debt)',
    ),
    Flag(
        name="todo_marker",
        category="todo",
        severity="low",
        pattern=re.compile(r"(?://|/\*)\s*(?:TODO|FIXME|HACK)\b",
                           re.IGNORECASE),
        description="TODO/FIXME/HACK marker",
    ),
    # -- security / interop --------------------------------------------------
    Flag(
        name="fileio_permission",
        category="security",
        severity="medium",
        pattern=re.compile(r"\bnew\s+FileIOPermission\b", re.IGNORECASE),
        description="FileIOPermission assertion (file system access)",
    ),
    Flag(
        name="winapi_usage",
        category="security",
        severity="medium",
        # :: restricts to actual static calls; a bare WinAPI word also
        # appears in comments and would over-flag.
        pattern=re.compile(r"\bWinAPI(?:Server)?::"),
        description="WinAPI/WinAPIServer call (client/server interop debt)",
    ),
    Flag(
        name="system_io",
        category="security",
        severity="low",
        # System.IO from X++ is common and often fine in tooling; low
        # severity, but it maps the file-access surface for the audit.
        pattern=re.compile(r"\bSystem\.IO\."),
        description="System.IO.* usage from X++ (file access surface)",
    ),
]

# Dropped patterns (documented so nobody re-adds them blind):
# - bare `executeQuery\s*\(`: majority false positive; FormDataSource
#   .executeQuery() is idiomatic form-refresh code. Replaced by the
#   statement-scoped variant above.
# - `\bstr\s+sql\b`: zero hits in the tuning corpus and prone to matching
#   unrelated variable declarations; createStatement covers the real cases.
# - single-hit `\bcontainer\b`: flagged ~10% of all methods; raised to a
#   3-line threshold.


def tts_mismatch(source: str) -> Optional[Tuple[int, str]]:
    """ttsbegin/ttscommit count mismatch within one method body.

    Caveat: a method may legitimately open a transaction another method
    closes, but in most corpora an unbalanced count inside one body is
    worth a human look, so it is reported as medium.
    """
    low = source.lower()
    begins = len(re.findall(r"\bttsbegin\b", low))
    # ttsabort is a legitimate closer (verified: the tuning corpus uses it
    # in exception-demo code); counting only ttscommit false-positives.
    closes = len(re.findall(r"\btts(?:commit|abort)\b", low))
    if begins != closes and (begins or closes):
        return (begins, f"ttsbegin={begins} ttscommit/abort={closes}")
    return None
