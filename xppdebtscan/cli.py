"""CLI entrypoint: ``python -m xppdebtscan --pld <path> --out <dir>``.

Parses the PackagesLocalDirectory tree in memory, runs the debt rule set
over every method body, and writes:

    findings.json
    findings.md
    heatmap.md
"""

import argparse
import json
import os
import sys

from . import pld, scanner


def _write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="xppdebtscan",
        description="Free deterministic tech-debt scanner for D365 F&O "
                    "X++ codebases")
    ap.add_argument("--pld", required=True,
                    help="root of the PackagesLocalDirectory-style tree "
                         "(or any folder holding <Package>/<Model>/Ax*/ "
                         "element XML)")
    ap.add_argument("--out", required=True, help="output directory")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.pld):
        print(f"not a directory: {args.pld}", file=sys.stderr)
        return 1
    os.makedirs(args.out, exist_ok=True)

    debt = scanner.scan_elements(pld.iter_elements(args.pld))

    _write(os.path.join(args.out, "findings.json"),
           json.dumps(debt, indent=2, ensure_ascii=False) + "\n")
    _write(os.path.join(args.out, "findings.md"),
           scanner.render_findings_md(debt))
    _write(os.path.join(args.out, "heatmap.md"),
           scanner.build_heatmap(debt))

    print(json.dumps({"total_findings": debt["total_findings"],
                      "by_flag": debt["by_flag"],
                      "by_severity": debt["by_severity"],
                      "elements_scanned": debt["elements_scanned"],
                      "methods_scanned": debt["methods_scanned"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
