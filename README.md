# AI Projects

A collection of independent AI-related tools built and maintained by Levi B Mackay. Each project started as a real problem — course planning, TA grading workflows, code review, home-server monitoring — and became a chance to work with APIs, web scraping, CLI/TUI tooling, and AI-model integration. Projects are unrelated to each other and each keeps its own setup, dependencies, and history.

---

## Projects

### [byui-planner](./byui-planner)

A command-line tool for planning a class schedule at BYU-Idaho — searches the live course schedule, pulls professor ratings from Rate My Professor, and filters sections against preferences (morning-only, Friday-free, etc.).

**Tech stack:** Python, Typer (CLI), Rich, Requests, BeautifulSoup4, RateMyProfessorAPI, python-dotenv

### [canvas-risk](./canvas-risk)

A terminal dashboard (CLI + Textual TUI) that connects to the Canvas LMS API and flags students at risk of falling behind, using a weighted risk engine over missing assignments, grade trends, late submissions, and inactivity. Caches data locally in SQLite for offline viewing and trend analysis.

**Tech stack:** Python, Typer, Textual, Rich, Requests, SQLAlchemy, Pandas, SQLite

### [canvas-ta-tool](./canvas-ta-tool)

A terminal dashboard for TAs and instructors managing a Canvas course — missing/late assignments, ungraded submissions, grade breakdowns, and per-student lookups, all from the command line with a Rich-powered UI.

**Tech stack:** Python, Rich, Requests, python-dotenv, curses

### [code-reviewer](./code-reviewer)

An AI-powered code review CLI that gives expert feedback on any file, backed by multiple free AI providers (Groq/Llama 3.3 70B, Google Gemini 1.5 Flash, or local Ollama). Supports full/quick/security/performance/roast review modes, interactive follow-up chat, a multi-model mode that merges results across providers, and saves every review to local history.

**Tech stack:** Python, Typer, Rich, Groq SDK, google-generativeai, Ollama, Pygments

### [pipulse](./pipulse)

A FastAPI web service ("PiPulse Mission Control") that serves a small dashboard for live system monitoring (CPU, memory, network I/O via psutil) alongside Spotify now-playing integration, intended to run as a background service (see `pipulse.service`, `install.sh`).

**Tech stack:** Python, FastAPI, Uvicorn, psutil, Spotipy, python-dotenv

---

## Tech stack overview

Every project here is a Python CLI, TUI, or lightweight service — most built on Typer and/or Rich for their terminal interfaces, with `python-dotenv` for local configuration. Beyond that shared foundation, each project has its own purpose-specific dependencies (web scraping, Canvas API clients, AI provider SDKs, FastAPI), so there's no single unifying framework across the whole repo.

---

## Setup

Each project has its own setup instructions and dependencies — see the project's own directory/README linked above. In general, each is a standalone Python project with its own `requirements.txt`:

```bash
cd <project-name>
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python main.py --help
```

Some projects (e.g. `canvas-risk`, `canvas-ta-tool`) also require a `.env` file with API credentials — see that project's `.env.example`/README for details.

---

## Development

Contributing and development standards are documented in [CONTRIBUTING.md](./CONTRIBUTING.md).
Release notes and upcoming changes are tracked in [CHANGELOG.md](./CHANGELOG.md).

CI runs on every pull request, push to `main`, and version tag (`v*`) via [`.github/workflows/python-ci.yml`](./.github/workflows/python-ci.yml). Before opening a PR, run the same checks locally for any project you touched.

---

## Author

Levi B Mackay ([@levibmackay](https://github.com/levibmackay))

_Last updated: 2026-07-19_
