# Contributing

This repository contains multiple independent Python CLI projects. Make focused changes, and only update the project(s) your PR touches.

## 1) Local setup

Use Python 3.11 (matches CI).

```bash
cd <project-name>
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
```

For `canvas-risk`, install dev dependencies too:

```bash
venv/bin/pip install -r requirements-dev.txt
```

## 2) Quality gates (must pass)

Run checks only for the project(s) you changed.

- `canvas-risk`:

  ```bash
  cd canvas-risk
  venv/bin/pytest -q
  ```

- `byui-planner`, `code-reviewer`, `canvas-ta-tool`, `pipulse`:

  ```bash
  cd <project-name>
  venv/bin/python -m compileall -q .
  ```

These checks mirror CI in `.github/workflows/python-ci.yml`.

## 3) Branch and pull request guidance

- Create a descriptive branch from `main` (example: `docs/contributing-update`).
- Keep PRs scoped to one logical change.
- Include a short summary of what changed and how you validated it.
- If behavior, setup, or commands changed, update docs in the same PR.

## 4) PR checklist

- [ ] Relevant local checks passed for every touched project
- [ ] CI is green
- [ ] Documentation updated when needed
- [ ] No unrelated files or refactors included

## 5) Release process

This repository uses tag-based releases and keeps release notes in `CHANGELOG.md`.

1. Ensure all intended changes are merged to `main` and CI is green.
2. Update `CHANGELOG.md` under `## [Unreleased]` (use `Added`, `Changed`, `Fixed` as needed).
3. Create and push a semantic version tag (example: `v1.2.0`).
4. On tag push, `.github/workflows/python-ci.yml` runs full test/smoke checks plus a `release-quality-gate` job.
5. If the workflow passes, cut the GitHub release and use the changelog entries as release notes.
