# AI Projects

A collection of tools I built as a Computer Science student at BYU-Idaho. Each project solves a real problem I was dealing with and gave me a chance to work with APIs, web scraping, CLI tooling, and AI.

---

## Projects

### code-reviewer

An AI-powered code review tool that gives expert feedback on any code you paste or point it at. Supports multiple free AI providers, multiple review modes, interactive follow-up chat, and saves every review to local history.

**Providers (all free)**
- Groq with Llama 3.3 70B — fastest, best quality, free tier at console.groq.com
- Google Gemini 1.5 Flash — free tier at aistudio.google.com
- Ollama — runs locally on your machine, completely unlimited

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
- Security audit targeting OWASP top 10 and common vulnerabilities
- Performance analysis with Big O breakdowns
- Roast mode for when you need brutal honesty with real fixes
- Interactive chat so you can ask follow-up questions after any review
- Multi-model mode that runs all available providers and merges the results
- Auto-detects programming language from your code
- Saves every review as a markdown file with full history browsing

---

### byui-planner

A command line tool for planning your class schedule at BYUI. It searches the live course schedule, pulls professor ratings from Rate My Professor, and filters sections based on your preferences.

**Usage**

```bash
cd byui-planner
python main.py search "CSE 212"
python main.py plan --term "Fall Semester 2026"
python main.py complete "CSE 111"
python main.py remaining
```

**Features**
- Searches BYUI course schedule in real time
- Fetches and caches Rate My Professor ratings for every professor
- Filters for morning sections and Friday-free schedules by default
- Tracks which courses you have left based on your degree requirements

---

### canvas-risk

A CLI tool that connects to the Canvas LMS API and helps you track where you are at risk of falling behind. It flags ungraded work, missing assignments, and grade trends so nothing sneaks up on you at the end of the semester.

---

## Tech Stack

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
