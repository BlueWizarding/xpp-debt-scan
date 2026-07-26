"""Debt scan over parsed PLD elements, plus rendering helpers.

Same deterministic rule set as the Bluewizarding audit's debt pass: the
same inputs always produce the same outputs. No model calls, no network,
no database.
"""

from collections import Counter
from typing import Dict, Iterable, List, Optional, Tuple

from .rules import FLAGS, SEVERITIES, line_hits, tts_mismatch


def scan_elements(elements: Iterable[Dict]) -> Dict:
    """Regex-scan every element's method source; returns all findings."""
    findings: List[Dict] = []
    runbase_reported = set()
    element_count = 0
    method_count = 0
    for e in elements:
        element_count += 1
        for m in e["methods"]:
            method_count += 1
            src = m["source"] or ""
            base = {"element": e["name"], "method": m["name"],
                    "type": e["type"], "package": e["package"],
                    "model": e["model"]}
            for fl in FLAGS:
                hits = line_hits(fl.pattern, src)
                if len(hits) >= fl.min_hits:
                    findings.append({**base, "flag": fl.name,
                                     "category": fl.category,
                                     "severity": fl.severity,
                                     "line": hits[0][0],
                                     "match": hits[0][1],
                                     "hit_count": len(hits)})
            tts = tts_mismatch(src)
            if tts:
                findings.append({**base, "flag": "tts_mismatch",
                                 "category": "legacy", "severity": "medium",
                                 "line": tts[0], "match": tts[1],
                                 "hit_count": 1})
        # RunBase lineage: reported once per element, not per method.
        ext = (e.get("extends") or "")
        if ext.lower().startswith("runbase") and \
                e["name"] not in runbase_reported and e["methods"]:
            runbase_reported.add(e["name"])
            findings.append({"element": e["name"], "method": "(class)",
                             "type": e["type"], "package": e["package"],
                             "model": e["model"],
                             "flag": "runbase_lineage",
                             "category": "legacy", "severity": "medium",
                             "line": 0,
                             "match": f"extends {ext} "
                                      "(SysOperation is the modern frame)",
                             "hit_count": 1})
    by_flag = Counter(f["flag"] for f in findings)
    by_severity = Counter(f["severity"] for f in findings)
    return {"findings": findings, "by_flag": dict(by_flag),
            "by_severity": dict(by_severity),
            "total_findings": len(findings),
            "elements_scanned": element_count,
            "methods_scanned": method_count}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_HEAT_EMOJI = {"high": "\U0001F534", "medium": "\U0001F7E0",
               "low": "\U0001F7E1", "none": "\U0001F7E2"}


def _cell(count: int, worst: Optional[str]) -> str:
    if count == 0:
        return _HEAT_EMOJI["none"] + " 0"
    return _HEAT_EMOJI.get(worst or "low", _HEAT_EMOJI["low"]) + f" {count}"


def build_heatmap(debt: Dict) -> str:
    """Markdown severity matrix: rows = models, cols = finding categories."""
    categories = sorted({fl.category for fl in FLAGS})
    models = sorted({f["model"] for f in debt["findings"]})
    sev_rank = {s: i for i, s in enumerate(SEVERITIES)}

    # (model, category) -> [count, worst_severity]
    cells: Dict[Tuple[str, str], List] = {}
    for f in debt["findings"]:
        cur = cells.setdefault((f["model"], f["category"]), [0, None])
        cur[0] += 1
        sev = f["severity"]
        if sev in sev_rank and (cur[1] is None
                                or sev_rank[sev] < sev_rank[cur[1]]):
            cur[1] = sev

    lines = ["# Debt heatmap", "",
             "Cells: count of findings; color = worst severity in the cell "
             "(\U0001F534 high, \U0001F7E0 medium, \U0001F7E1 low, "
             "\U0001F7E2 none).", "",
             "| Model | " + " | ".join(categories) + " |",
             "|---|" + "---|" * len(categories)]
    for model in models:
        row = [model]
        for cat in categories:
            count, worst = cells.get((model, cat), (0, None))
            row.append(_cell(count, worst))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def render_findings_md(debt: Dict) -> str:
    lines = ["# Technical debt scan", "",
             f"Elements scanned: **{debt['elements_scanned']}**, "
             f"methods scanned: **{debt['methods_scanned']}**", "",
             f"Total findings: **{debt['total_findings']}**", "",
             "## By flag", "", "| Flag | Count |", "|---|---|"]
    for flag, c in sorted(debt["by_flag"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| {flag} | {c} |")
    lines += ["", "## By severity", "", "| Severity | Count |", "|---|---|"]
    for sev in SEVERITIES:
        lines.append(f"| {sev} | {debt['by_severity'].get(sev, 0)} |")
    lines += ["", "## Findings", "",
              "| Severity | Flag | Element | Method | Line | Match |",
              "|---|---|---|---|---|---|"]
    order = {s: i for i, s in enumerate(SEVERITIES)}
    for f in sorted(debt["findings"],
                    key=lambda f: (order.get(f["severity"], 9),
                                   f["flag"], f["element"], f["method"])):
        match = f["match"].replace("|", "\\|")
        lines.append(f"| {f['severity']} | {f['flag']} | {f['element']} "
                     f"| {f['method']} | {f['line']} | `{match}` |")
    return "\n".join(lines) + "\n"
