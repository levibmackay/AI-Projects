# Code Reviewer

An AI-powered code review tool that gives you expert feedback on your code using free AI models. Supports multiple providers, multiple review modes, interactive chat, and saves every review to your local history.

---

## Features

- Full reviews covering bugs, security, performance, code quality, and top improvements
- Quick mode for fast top-3 issues
- Security audit mode targeting OWASP top 10 and common vulnerabilities
- Performance analysis with Big O breakdowns
- Roast mode because sometimes you need brutal honesty
- Interactive chat so you can ask follow-up questions after the review
- Multi-model mode that runs all available providers and merges the results
- Auto-detects programming language from your code
- Saves every review to local history with full markdown export
- Works with files, piped input, or paste directly in the terminal

---

## Free AI Providers

All providers used are free. No paid API required.

| Provider | How to get key | Limits |
|----------|---------------|--------|
| Groq | console.groq.com | 14,400 req/day, very fast |
| Gemini 1.5 Flash | aistudio.google.com | 1,500 req/day |
| Ollama | ollama.com (local) | Unlimited, runs on your machine |

---

## Setup

```bash
cd code-reviewer
python3 -m venv venv
venv/bin/pip install -r requirements.txt

cp .env.template .env
# Add your API keys to .env
```

---

## Usage

```bash
# Review a file
venv/bin/python main.py review mycode.py

# Paste code interactively
venv/bin/python main.py review

# Pipe code in
cat mycode.py | venv/bin/python main.py review

# Review modes
venv/bin/python main.py review mycode.py --mode quick
venv/bin/python main.py review mycode.py --mode security
venv/bin/python main.py review mycode.py --mode performance
venv/bin/python main.py review mycode.py --mode roast

# Shortcuts for modes
venv/bin/python main.py quick mycode.py
venv/bin/python main.py security mycode.py
venv/bin/python main.py roast mycode.py

# Review then drop into chat for follow-up questions
venv/bin/python main.py review mycode.py --chat

# Interactive chat session
venv/bin/python main.py chat mycode.py

# Run all available models and merge results
venv/bin/python main.py review mycode.py --multi

# Pick a specific provider
venv/bin/python main.py review mycode.py --agent groq
venv/bin/python main.py review mycode.py --agent gemini
venv/bin/python main.py review mycode.py --agent ollama

# View past reviews
venv/bin/python main.py history
venv/bin/python main.py history --show <review-id>

# Check which providers are active
venv/bin/python main.py providers
```

---

## Multi-Model Mode

Running with `--multi` sends your code to every configured provider independently then uses the primary model to merge the results. Issues that multiple models agree on get flagged as high confidence. This gives you the most thorough review possible.

---

Built by Levi Mackay
