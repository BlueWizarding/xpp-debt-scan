import json
import os

from xppdebtscan import pld, scanner
from xppdebtscan.cli import main


def _scan(pld_root):
    return scanner.scan_elements(pld.iter_elements(pld_root))


def test_parser_yields_only_parseable_elements(pld_root):
    elements = list(pld.iter_elements(pld_root))
    names = {e["name"] for e in elements}
    assert names == {"DemoDirtyClass", "DemoCleanClass"}  # Broken.xml skipped
    dirty = next(e for e in elements if e["name"] == "DemoDirtyClass")
    assert dirty["extends"] == "RunBaseBatch"
    assert len(dirty["methods"]) == 4
    assert dirty["package"] == "DemoPkg"
    assert dirty["model"] == "DemoModel"


def test_expected_flags_fire(pld_root):
    debt = _scan(pld_root)
    by_flag = debt["by_flag"]
    assert by_flag["raw_sql_statement"] == 1
    assert by_flag["raw_sql_execute"] == 1
    assert by_flag["select_forupdate"] == 1
    assert by_flag["container_heavy"] == 1      # 3-line threshold met
    assert by_flag["todo_marker"] == 1
    assert by_flag["hardcoded_error_literal"] == 1
    assert by_flag["fileio_permission"] == 1
    assert by_flag["winapi_usage"] == 1
    assert by_flag["system_io"] == 1
    assert by_flag["infolog_direct"] == 1
    assert by_flag["runbase_lineage"] == 1
    assert by_flag["tts_mismatch"] == 1         # updateRecord: begin, no close


def test_false_positive_boundaries_hold(pld_root):
    debt = _scan(pld_root)
    clean = [f for f in debt["findings"] if f["element"] == "DemoCleanClass"]
    # balancedTts: ttsabort counted as closer -> no mismatch.
    # formRefresh: datasource executeQuery -> no raw_sql_execute;
    # one container line -> below the 3-line threshold;
    # throw error("@SYS...") -> label reference, not a literal.
    assert clean == []


def test_severity_totals(pld_root):
    debt = _scan(pld_root)
    assert debt["by_severity"]["high"] == 2
    assert debt["total_findings"] == 12
    assert debt["elements_scanned"] == 2
    assert debt["methods_scanned"] == 6


def test_cli_outputs(pld_root, tmp_path):
    out = str(tmp_path / "out")
    assert main(["--pld", pld_root, "--out", out]) == 0
    for fn in ("findings.json", "findings.md", "heatmap.md"):
        assert os.path.exists(os.path.join(out, fn))
    with open(os.path.join(out, "findings.json"), encoding="utf-8") as fh:
        payload = json.load(fh)
    assert payload["total_findings"] == 12
    heat = open(os.path.join(out, "heatmap.md"), encoding="utf-8").read()
    assert "DemoModel" in heat and "\U0001F534" in heat


def test_heatmap_worst_severity_wins(pld_root):
    debt = _scan(pld_root)
    heat = scanner.build_heatmap(debt)
    # direct_sql cell for DemoModel contains a high finding -> red emoji.
    row = next(l for l in heat.splitlines() if l.startswith("| DemoModel"))
    cells = [c.strip() for c in row.split("|")[2:-1]]
    categories = sorted({fl.category for fl in scanner.FLAGS})
    direct_sql = cells[categories.index("direct_sql")]
    assert direct_sql.startswith("\U0001F534")
