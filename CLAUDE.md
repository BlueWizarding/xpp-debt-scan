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

## Git home

This repo's home is the estate's own Forgejo server: `https://git.int.bluewizarding.com/bluewizard/xpp-debt-scan` (the `origin` remote).
It moved from GitHub on 2026-11-13. Check with `git remote -v`.

- GitHub (`BlueWizarding/xpp-debt-scan`) is a copy. Forgejo pushes every commit to it, because it is the public copy that people clone.
- Never push to GitHub directly. Push to `origin`; the copy follows, and a branch that exists only on GitHub is removed at the next sync.
- Workflows on the GitHub copy that trigger on a push still run. Ones that trigger on a GitHub pull request do not, because pull requests now live on Forgejo.
- Open and merge pull requests on Forgejo through its API, not `gh`. The merge into `main` is still the operator's gate.
- Issues were not moved. Any GitHub Issues for this repo are still on GitHub.
- Estate rule: `~/.claude/rules/forgejo-is-home.md`.
