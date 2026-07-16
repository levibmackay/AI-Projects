# AI Projects

A collection of tools I built as a Computer Science student at BYU-Idaho. Each one started as a real problem I was dealing with, and became a chance to work with APIs, web scraping, CLI tooling, and AI.

---

## Projects

### code-reviewer

An AI-powered code review tool that gives expert feedback on any file you point it at. Supports multiple free AI providers, several review modes, interactive follow-up chat, and saves every review to local history.

**Providers (all free)**
- Groq with Llama 3.3 70B — fastest, best quality, free tier at console.groq.com
- Google Gemini 1.5 Flash — free tier at aistudio.google.com
- Ollama — runs locally, completely unlimited

**Usage**
```bash
cd code-reviewer
python main.py review myfile.py
python main.py quick myfile.py
python main.py security myfile.py
python main.py roast myfile.py
python main.py review myfile.py --chat
python main.py review myfile.py --multi
python main.py history
```

**Features**
- Full reviews covering bugs, security, performance, code quality, and top improvements
- Quick mode for a fast top-3 breakdown
- Security audit targeting the OWASP top 10 and other common vulnerabilities
- Performance analysis with Big O breakdowns
- Roast mode for brutal honesty with real fixes attached
- Interactive chat for follow-up questions after any review
- Multi-model mode that runs every provider and merges the results
- Auto-detects programming language from the code itself
- Saves every review as a markdown file with full history browsing

---

### byui-planner

A command line tool for planning a class schedule at BYU-Idaho. Searches the live course schedule, pulls professor ratings from Rate My Professor, and filters sections based on preferences.

**Usage**
```bash
cd byui-planner
python main.py search "CSE 212"
python main.py plan --term "Fall Semester 2026"
python main.py complete "CSE 111"
python main.py remaining
```

**Features**
- Searches the BYU-Idaho course schedule in real time
- Fetches and caches Rate My Professor ratings for every professor
- Filters for morning sections and Friday-free schedules by default
- Tracks remaining courses against degree requirements

---

### canvas-risk

A CLI tool that connects to the Canvas LMS API and flags where a student is at risk of falling behind. Surfaces ungraded work, missing assignments, and grade trends so nothing sneaks up at the end of the semester.

---

### canvas-ta-tool

A terminal dashboard for TAs and instructors managing a Canvas course. Shows missing assignments, ungraded submissions, grade breakdowns, and individual student lookups, all from the command line with a clean Rich UI.

**Usage**
```bash
cd canvas-ta-tool
cp .env.example .env   # add your Canvas URL and API token
python canvas_ta.py
```

**Features**
- Missing & Late Assignments — every student with missing or late work, sorted by severity
- Needs Grading — grouped by assignment, oldest submission first
- Grade Analysis — every student below an A with their biggest point losses, closest gap first
- Student Lookup — search by name for a full per-assignment breakdown
- Refresh data or switch courses without restarting
- Paginated Canvas API client handles any class size

---

## Tech stack

Python, Typer, Rich, Requests, BeautifulSoup, SQLAlchemy, Groq, Gemini, Ollama, RateMyProfessorAPI

---

## Setup

Each project has its own virtual environment and requirements file.

```bash
cd <project-name>
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python main.py --help
```

---

Built and maintained by Levi Mackay
