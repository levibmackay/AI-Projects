# Internal Notes

Freeform engineering notes for my own future reference. Not for public consumption —
see README.md for the polished overview. Last reviewed: 2026-07-20.

---

## byui-planner

**State:** Functional, has a real test suite (`tests/`), feels the most "finished" of the
five projects.

- Commands: `search`, `plan`, `remaining`, `complete` (Typer app in `main.py`).
- `plan` walks `get_remaining_courses()` and calls the scraper once per course
  sequentially — no concurrency. Fine for a handful of remaining courses; would get
  slow if run against a full unfinished degree.
- Per-course failures during `plan` are caught and logged as a warning, then that
  course is skipped (empty list) rather than aborting the whole run — reasonable
  degradation, worth keeping.
- Completed/remaining course state lives in `data/completed_courses.json` +
  `data/degree_requirements.json`, checked into git. Fine for personal use; would
  need to move to `.gitignore` + `.env`-style local state if this were ever shared.
- Next steps ideas: cache RMP lookups (same professor gets re-fetched every run across
  different courses/terms); consider async/concurrent section search if the remaining-
  course list grows.

## canvas-risk

**State:** Has its own README (left untouched per scope). Biggest of the five in terms
of internal structure (`api/`, `database/`, `analytics/`, `ui/`, `commands/`).

- **Drift spotted, not fixed (out of scope — it's canvas-risk's own README):**
  `analytics/risk_engine.py`'s `RiskEngine.WEIGHTS` is
  `{grade: 40%, missing: 30%, trend: 10%, inactivity: 10%, peer_comparison: 10%}`,
  but `canvas-risk/README.md` documents the weights as missing 40% / grade trends 30% /
  late 20% / inactivity 10% (no peer_comparison, no separate "late" bucket). Either the
  engine was reworked after the README was written or the README was aspirational from
  the start. Worth reconciling directly in canvas-risk/README.md at some point.
- SQLite caching: `DatabaseManager.sync_from_canvas()` upserts by `canvas_id` (query-then-
  insert-or-update), not a bulk upsert — fine at course-roster scale, wouldn't scale past
  a few thousand rows but that's not this project's problem.
- `RiskEngine.categorize_student` emits emoji-prefixed profile tags ("🌟 High Achiever",
  "👻 The Ghost", etc.) baked into application logic, not just the TUI layer — if the tag
  strings are ever matched on elsewhere (tests, CLI filters), the emoji is now part of the
  contract, not decoration.
- Next steps ideas: reconcile the weight discrepancy above; `simulate_student_outcome`
  (what-if grade simulator) isn't mentioned anywhere in the README — worth exposing as a
  documented CLI command if it's meant to be user-facing rather than just a library
  function.

## canvas-ta-tool

**State:** Single-file (`canvas_ta.py`, ~1270 lines) plus `canvas_api.py`/`canvas_config.py`.
No per-project README yet — this is the thinnest-documented of the three without one.

- **Why curses AND Rich, not just one:** Rich draws every static screen (tables, menus,
  panels) but has no notion of a live-scrolling full-screen viewport with per-keystroke
  input. The one screen that needs that — the AI-risk submission pager
  (`_draw_code_pager`) — drops into raw `curses.wrapper(...)` for just that screen, then
  returns to the Rich-driven menu loop. Deliberate split, not leftover cruft: Rich for
  layout, curses for the one interactive pager.
- The "AI usage risk" feature (`compute_ai_analysis`, `score_submission`,
  `analyze_prose`/`analyze_code`) is a heuristic triage tool, explicitly disclaimed in the
  UI (`AI_DISCLAIMER` constant) as "not proof of AI use." It only looks at assignments
  matching `PROVE_ASSIGNMENT_RE` (name contains "prove") — hardcoded to this course's
  weekly Learn/Prove structure; would silently analyze nothing on a course that doesn't
  name assignments that way. Worth surfacing as a config option (assignment-name pattern)
  if this tool is ever pointed at a different course.
- Baselines for the style-shift signal only use a student's submissions *before* the one
  being scored (comment in code confirms this was a deliberate fix — early assignments
  were previously flagged for "jumping" above an average pulled down by harder work later
  in the term). Good example of a subtle correctness bug that was caught and fixed; don't
  regress it.
- Binary submission formats (PDF/DOCX/images) are skipped entirely for the AI-risk
  scan — no extraction dependency was added for those, so they show up as "no
  extractable text" and fall back to grade-pattern-only scoring.
- No test suite for this project (unlike byui-planner). Given how much scoring logic
  lives in `score_submission`/`analyze_prose`/`analyze_code`, this is the one gap I'd
  actually call out — not generic "add tests," specifically: the risk-scoring math has
  no coverage and would be easy to silently break while iterating on it.
- Next steps ideas: add a per-course config for the "Prove" assignment name pattern;
  consider a small test module for `score_submission` given prior/without-prior cases
  (there's already a natural boundary at `MIN_PRIOR_SAMPLES = 3`).

## code-reviewer

**State:** Has its own README (left untouched per scope). Cleanest multi-provider design
of the five projects.

- Provider fallback (`agents/router.py`): `get_agent()` tries the preferred provider first
  (if specified and available), then falls through Groq → Gemini → Ollama in that fixed
  order via `is_available()` checks. `get_all_available()` (used by multi-model mode)
  swallows any exception per-provider so one misconfigured provider doesn't take down the
  others — reasonable isolation.
- Free-tier limits documented in code-reviewer/README.md (Groq 14,400 req/day, Gemini
  1,500 req/day, Ollama unlimited/local) are provider-stated numbers, not something this
  codebase enforces or tracks — no rate-limit handling visible in the agent classes, so a
  provider outage or rate-limit hit likely surfaces as a raw exception rather than a clean
  fallback mid-request (fallback only happens at agent *selection* time, not mid-review).
- Next steps ideas: if a provider gets rate-limited mid-review it currently isn't retried
  against the next provider automatically — only picked once at start. Worth deciding if
  that's desired (fail fast) or should also fall back like the initial selection does.

## pipulse

**State:** Single-file FastAPI app (`main.py`), meant to run as a systemd service on a
Raspberry Pi (`pipulse.service`, `install.sh`).

- Every optional integration (Spotify, Pi-hole) checks its own required env vars up front
  and returns `{"status": "unconfigured", "message": "...missing env vars: ..."}` instead
  of raising — good pattern, keeps the dashboard usable with only a subset of integrations
  configured. The `/api/external` (NASA APOD + weather) endpoint doesn't follow this
  pattern since neither API needs credentials (weather is wttr.in, NASA uses the public
  `DEMO_KEY`) — errors there are caught per-sub-call and reported as `*_error` keys instead.
- NASA integration hardcodes `api_key=DEMO_KEY` — this is NASA's public shared demo key,
  rate-limited across everyone using it (not project-specific), not a leaked secret. Would
  be worth moving to a real (free) NASA API key via env var if APOD calls ever start
  getting rate-limited by other DEMO_KEY users.
- Spotify token refresh is done manually via a raw POST to Spotify's token endpoint rather
  than through spotipy's own OAuth helper — intentional, since this runs headless with a
  pre-obtained refresh token and no browser to complete a normal OAuth flow.
- The README previously undersold this project (only mentioned CPU/memory/network +
  Spotify) — Pi-hole and the NASA/weather proxy were undocumented features already in the
  code. Fixed in the top-level README as part of this pass.
- Next steps ideas: `/api/stats` network-speed calculation resets `net_state` globally on
  every request with no locking — fine for a single-user dashboard polled by one browser,
  would misbehave under concurrent pollers (multiple browser tabs open at once would each
  perturb the delta the other is computing).

## Repo-wide

- CHANGELOG.md's `[Unreleased]` section is still template placeholder text
  ("_Add new features here before cutting the next release._") — nobody has been filling
  it in per-change. Left as-is per task scope; flagging because it means the changelog
  isn't actually tracking anything right now beyond the one "routine maintenance" entry.
- No TODO/FIXME/XXX markers found anywhere in the five projects' own source (checked all
  non-vendored `.py` files) — either genuinely clean or nobody's been leaving markers
  instead of just fixing things inline.
- All five projects vendor their `venv`/`.venv` directories on disk but they're properly
  gitignored (`venv/` in top-level `.gitignore`) — not committed, just local clutter.
