# xpp-debt-scan

Free deterministic tech-debt scanner for Dynamics 365 F&O X++ codebases.

Point it at a PackagesLocalDirectory-style metadata tree and it parses the
AOT element XML in memory, runs a tuned rule set over every method body,
and writes `findings.json`, `findings.md`, and an emoji severity
`heatmap.md` per model. Pure Python standard library, no dependencies, no
database, no network, no model calls. The same inputs always produce the
same outputs.

Built from 11 years in Dynamics AX and D365 F&O codebases. This is the open
half of the [Bluewizarding AI-Accelerated X++ Codebase Audit](https://bluewizarding.com/audit).

## Quickstart

Python 3.9+ and nothing else.

```
git clone https://github.com/BlueWizarding/xpp-debt-scan
cd xpp-debt-scan
python -m xppdebtscan --pld <path-to-PackagesLocalDirectory> --out out
```

`--pld` accepts a full PackagesLocalDirectory or any folder holding
`<Package>/<Model>/Ax*/Element.xml` trees (an ISV source repo works fine).
`XppMetadata`, `bin`, `Resources`, `Reports`, and `WebContent` are skipped.

Outputs:

| File | Contents |
|---|---|
| `findings.json` | every finding with element, method, line, matched text, severity |
| `findings.md` | the same as a readable report, sorted worst first |
| `heatmap.md` | per-model severity matrix, worst severity colors the cell |

## Sample output

Run against [TrudAX/XppTools](https://github.com/TrudAX/XppTools), a public
open-source D365 F&O tooling suite (454 elements, 1738 methods): 258
findings (8 high, 159 medium, 91 low).

```
# Debt heatmap

Cells: count of findings; color = worst severity in the cell (🔴 high, 🟠 medium, 🟡 low, 🟢 none).

| Model | direct_sql | legacy | localization | security | todo |
|---|---|---|---|---|---|
| DEVBatchControlUtil | 🟢 0 | 🟠 3 | 🟠 2 | 🟢 0 | 🟢 0 |
| DEVCallStackInfolog | 🟠 2 | 🟠 2 | 🟠 1 | 🟢 0 | 🟢 0 |
| DEVCommon | 🟢 0 | 🟡 3 | 🟠 9 | 🟠 9 | 🟢 0 |
| DEVCustomScripts | 🟢 0 | 🟠 2 | 🟠 3 | 🟡 2 | 🟢 0 |
| DEVDMFTools | 🟠 1 | 🟢 0 | 🟢 0 | 🟢 0 | 🟢 0 |
| DEVDocuExpImp | 🟢 0 | 🟠 7 | 🟠 8 | 🟡 3 | 🟢 0 |
| DEVExternalIntegration | 🔴 5 | 🟠 23 | 🟠 46 | 🟡 29 | 🟢 0 |
| DEVExternalIntegrationSamples | 🟠 9 | 🟠 2 | 🟠 28 | 🟡 6 | 🟢 0 |
| DEVLicenseUtils | 🟠 2 | 🟠 4 | 🟢 0 | 🟢 0 | 🟢 0 |
| DEVListOfValuesToRange | 🟢 0 | 🟡 1 | 🟢 0 | 🟢 0 | 🟢 0 |
| DEVRecordInfo | 🟢 0 | 🟢 0 | 🟠 3 | 🟢 0 | 🟢 0 |
| DEVSQLExecute | 🔴 5 | 🟡 3 | 🟠 2 | 🟡 3 | 🟢 0 |
| DEVSQLReports | 🔴 2 | 🟠 4 | 🟢 0 | 🟡 3 | 🟢 0 |
| DEVSysQueryFormAddRelInfo | 🟠 1 | 🟢 0 | 🟢 0 | 🟢 0 | 🟢 0 |
| DEVTools | 🟢 0 | 🟠 3 | 🟢 0 | 🟢 0 | 🟢 0 |
| DEVTutorial | 🟠 1 | 🟠 7 | 🟠 7 | 🟡 2 | 🟢 0 |
```

Note that a tooling suite like XppTools legitimately triggers several of
these rules on purpose (a SQL-execution utility contains raw SQL by
design). Findings are a map of where to look, not a verdict.

## Why these rules

Every rule was tuned against real method source first. The false-positive
boundary for each is stated honestly, because a scanner you cannot trust
to be quiet is a scanner you stop reading.

| Rule | Severity | What it catches | False-positive boundary |
|---|---|---|---|
| `raw_sql_statement` | high | `Connection.createStatement(` | The unambiguous raw-SQL door. Essentially none. |
| `raw_sql_execute` | high | `statement.executeQuery/executeUpdate` | A bare `executeQuery(` would be majority false positive: `FormDataSource.executeQuery()` is idiomatic form-refresh code. The rule requires the statement-object idiom on the same line. |
| `select_forupdate` | medium | `select ... forupdate` on one line | `forupdate` alone is legitimate X++. It is flagged medium because in tooling and utility layers it usually marks data-fixing scripts that bypass business logic. |
| `hardcoded_error_literal` | medium | `throw error("English literal")`, including `strFmt` | Label references (`"@SYS..."`) do not fire. Literals passed via variables are intentionally not chased. |
| `tts_mismatch` | medium | ttsbegin count differs from ttscommit plus ttsabort count in one method | `ttsabort` is counted as a legitimate closer; counting only `ttscommit` false-positives on exception handlers. A method may still legitimately open a transaction another method closes; that pattern will flag and deserves the human look anyway. |
| `runbase_lineage` | medium | class extends RunBase/RunBaseBatch (reported once per class) | RunBase still works; the flag marks migration distance to the SysOperation framework, not breakage. |
| `fileio_permission` | medium | `new FileIOPermission` | Maps the file-access surface. |
| `winapi_usage` | medium | `WinAPI::` / `WinAPIServer::` static calls | The `::` requirement keeps the word "WinAPI" in comments from over-flagging. |
| `container_heavy` | low | 3+ lines in one method mentioning container/conpeek/conpoke/conins/condel | A single container declaration is ordinary X++. A 1-hit threshold flagged roughly 10% of all methods in the tuning corpus, which is noise, so the threshold is 3 distinct lines. |
| `infolog_direct` | low | direct `infolog.*` calls | Prefer `info()`, `warning()`, `error()`. |
| `system_io` | low | `System.IO.*` from X++ | Common and often fine in tooling; kept low severity to map the surface. |
| `todo_marker` | low | `// TODO`, `FIXME`, `HACK` | Comment-anchored, so prose mentions rarely fire. |

Rules that were tried and deliberately dropped, so nobody re-adds them
blind: a bare `executeQuery(` pattern (majority false positive, see above),
a `str sql` declaration pattern (zero true hits, matched unrelated
variables), and the single-hit container rule (noise).

## What this tool deliberately does not do

This is the open half of a paid audit. The closed half needs a full stock
Microsoft metadata index and the analysis layers on top of it:

- Stock-index cross-reference: stock-vs-custom discrimination,
  overlayering and name-collision detection against the Microsoft baseline
- Upgrade-collision forecasting
- Verdicts and the prioritized decision sheet
- CI gate installation so the debt count only ratchets down

Those live in the [AI-Accelerated X++ Codebase Audit](https://bluewizarding.com/audit)
(fixed scope: $9,500, 1 week).

## Tests

```
python -m pytest tests
```

The suite builds a tiny synthetic PLD tree and asserts both that every
rule fires where it should and that the documented false-positive
boundaries hold (datasource `executeQuery` stays quiet, `ttsabort` closes
a transaction, one container line stays quiet, `"@SYS"` labels stay quiet).

## License

MIT, copyright Bluewizarding Consulting LLC 2026.
