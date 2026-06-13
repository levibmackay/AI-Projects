# AI Projects

A collection of tools I built as a Computer Science student at BYU-Idaho. Each project solves a real problem I was dealing with and gave me a chance to work with APIs, web scraping, and CLI tooling.

---

## Projects

### byui-planner

A command line tool for planning your class schedule at BYUI. It searches the live course schedule, pulls professor ratings from Rate My Professor, and filters sections based on your preferences like morning classes and no Friday schedule.

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

Python, Typer, Rich, Requests, BeautifulSoup, SQLAlchemy, RateMyProfessorAPI

---

## Setup

Each project has its own virtual environment and requirements file.

```bash
cd byui-planner
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python main.py --help
```

---

Built and maintained by Levi Mackay
