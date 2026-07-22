# AI Projects

A collection of independent AI-related tools built and maintained by Levi B Mackay. Each project started as a real problem — course planning, TA grading workflows, code review, home-server monitoring — and became a chance to work with APIs, web scraping, CLI/TUI tooling, and AI-model integration. Projects are unrelated to each other and each keeps its own setup, dependencies, and history.

---

## Projects

### [byui-planner](./byui-planner)

A command-line tool for planning a class schedule at BYU-Idaho — searches the live course schedule, pulls professor ratings from Rate My Professor, ranks sections by professor rating, and filters against preferences (morning-only, Friday-free). Tracks completed/remaining courses against a degree-requirements file so `plan` can build a schedule for every course you still need.

**Tech stack:** Python, Typer (CLI), Rich, Requests, BeautifulSoup4, RateMyProfessorAPI, python-dotenv

**Run:**
```bash
cd byui-planner
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python main.py --help
```

### [canvas-risk](./canvas-risk)

A terminal dashboard (CLI + Textual TUI) that connects to the Canvas LMS API and flags students at risk of falling behind, using a weighted risk engine over missing assignments (40%), grade trends (30%), late submissions (20%), and inactivity (10%). Caches data locally in SQLite so `dashboard`/`risk-report`/`ungraded` can run offline between syncs.

**Tech stack:** Python, Typer, Textual, Rich, Requests, SQLAlchemy, Pandas, SQLite

See [canvas-risk/README.md](./canvas-risk/README.md) for full setup and usage.

### [canvas-ta-tool](./canvas-ta-tool)

A terminal dashboard for TAs and instructors managing a Canvas course — missing/late assignments, ungraded submissions, grade breakdowns ("what's keeping students from an A"), and per-student lookups, all driven from a Rich-powered menu. Also includes a heuristic "AI usage risk" screen that flags weekly assignment submissions worth a second look (stock AI phrasing, unusually uniform structure, a style shift from a student's own prior work, or a sudden grade jump) with a full-screen curses code pager for reading the flagged submission in context. It's a triage hint, not a detector — every screen that surfaces it says so.

**Tech stack:** Python, Rich, Requests, python-dotenv, curses (for the submission pager)

**Run:**
```bash
cd canvas-ta-tool
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env   # add CANVAS_URL and CANVAS_TOKEN
venv/bin/python canvas_ta.py
```

### [code-reviewer](./code-reviewer)

An AI-powered code review CLI that gives expert feedback on any file, backed by multiple free AI providers (Groq, Google Gemini 1.5 Flash, or local Ollama) with automatic fallback between them. Supports full/quick/security/performance/roast review modes, interactive follow-up chat, a multi-model mode that merges results across providers, and saves every review to local history with markdown export.

**Tech stack:** Python, Typer, Rich, Groq SDK, google-generativeai, Ollama, Pygments

See [code-reviewer/README.md](./code-reviewer/README.md) for full setup and usage.

### [pipulse](./pipulse)

A FastAPI web service ("PiPulse Mission Control") that serves a small dashboard for live system monitoring (CPU, memory, disk, temperature, and network I/O via psutil), plus optional integrations that degrade gracefully to an "unconfigured" status when their env vars aren't set: Spotify now-playing, Pi-hole query stats, and a NASA APOD/weather proxy. Intended to run as a background service on a Raspberry Pi (see `pipulse.service`, `install.sh`).

**Tech stack:** Python, FastAPI, Uvicorn, psutil, Spotipy, Requests, python-dotenv

**Run:**
```bash
cd pipulse
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.template .env   # optional: Spotify/Pi-hole credentials
venv/bin/python main.py   # serves on http://0.0.0.0:8000
```

---

## Tech stack overview

Every project here is a Python CLI, TUI, or lightweight service — most built on Typer and/or Rich for their terminal interfaces, with `python-dotenv` for local configuration. Beyond that shared foundation, each project has its own purpose-specific dependencies (web scraping, Canvas API clients, AI provider SDKs, FastAPI), so there's no single unifying framework across the whole repo.

---

## Setup

Each project has its own setup instructions and dependencies — see the per-project sections above (or the project's own README, where one exists). In general, each is a standalone Python project with its own `requirements.txt` and its own entry-point script:

```bash
cd <project-name>
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Most projects (`canvas-risk`, `canvas-ta-tool`, `code-reviewer`, `pipulse`) also require a `.env` file with API credentials — copy the project's `.env.example`/`.env.template` and fill in the values before running.

---

## Development

Contributing and development standards are documented in [CONTRIBUTING.md](./CONTRIBUTING.md).
Release notes and upcoming changes are tracked in [CHANGELOG.md](./CHANGELOG.md).

CI runs on every pull request, push to `main`, and version tag (`v*`) via [`.github/workflows/python-ci.yml`](./.github/workflows/python-ci.yml). Before opening a PR, run the same checks locally for any project you touched.

---

## Author

Levi B Mackay ([@levibmackay](https://github.com/levibmackay))

_Last updated: July 22, 2026_

_Last reviewed: 2026-07-20 19:33 MDT_

---
**Last updated:** 2026-07-21
