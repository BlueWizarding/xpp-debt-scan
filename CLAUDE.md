# xpp-debt-scan agent notes

Public, deterministic X++ tech-debt scanner. Pure Python standard library, Python 3.9
floor, no network, no model calls. Identical input must always produce identical output.

## Project agents

- `xpp-debt-reviewer` (`.claude/agents/`): grounds every X++ claim in the `d365-codex`
  MCP index, hunts false positives and false negatives per rule, checks severity against
  rationale, checks fixture coverage, guards determinism. Dispatch it on any change to
  `xppdebtscan/rules.py` or `scanner.py` before opening the PR.

## Verify

```
python -m pytest -q
```

## Branching

Single `main` branch today (public OSS, low churn). Feature branches open a PR to `main`;
the operator merges. Provision `dev` and `test` if active development resumes, per the
estate branch-naming rule.
