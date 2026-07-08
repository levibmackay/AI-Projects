#!/usr/bin/env python3
"""One-off maintenance script: set the "Until" (lock_at) date on every
Assignment in a course to a fixed date/time, except assignments that live in
a specific module (e.g. a later week that shouldn't be locked early).

Due dates and "Available From" dates are left untouched — this only changes
when Canvas stops accepting submissions.

Usage:
    python3 set_until_dates.py              # dry run — shows the plan, changes nothing
    python3 set_until_dates.py --apply      # actually performs the updates
"""

import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.table import Table

from canvas_api import CanvasAPI

load_dotenv()
console = Console(width=190)

COURSE_NAME_MATCH = 'cse 111'
# Matches "W07", "Week 07", "Week7", "week 7", etc. — but not "Week 17"/"Week 27"
# thanks to the \b boundaries around the digits.
SKIP_MODULE_RE = re.compile(r'\bw(?:eek)?\s*0*7\b', re.IGNORECASE)
TARGET_YEAR, TARGET_MONTH, TARGET_DAY = 2026, 7, 18
TARGET_HOUR, TARGET_MINUTE = 23, 59  # 11:59 PM

# Canvas user profiles sometimes report a Rails ActiveSupport time zone name
# (e.g. "Mountain Time (US & Canada)") rather than an IANA name. Map the
# common US ones so we can localize correctly either way.
RAILS_TZ_MAP = {
    'Mountain Time (US & Canada)': 'America/Denver',
    'Pacific Time (US & Canada)': 'America/Los_Angeles',
    'Central Time (US & Canada)': 'America/Chicago',
    'Eastern Time (US & Canada)': 'America/New_York',
    'Arizona': 'America/Phoenix',
}


def resolve_timezone(api: CanvasAPI) -> ZoneInfo:
    profile = api.get_self_profile()
    tz_name = profile.get('time_zone') or 'America/Denver'
    iana = RAILS_TZ_MAP.get(tz_name, tz_name)
    try:
        return ZoneInfo(iana)
    except Exception:
        console.print(f'[yellow]Could not resolve Canvas timezone "{tz_name}" — defaulting to America/Denver.[/yellow]')
        return ZoneInfo('America/Denver')


def fmt_dt(iso: str, tz: ZoneInfo) -> str:
    if not iso:
        return '[dim]none[/dim]'
    dt = datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(tz)
    return dt.strftime('%b %d, %Y %I:%M %p')


def pick_course(api: CanvasAPI):
    courses = [
        c for c in api.get_ta_courses()
        if COURSE_NAME_MATCH in (c.get('name') or '').lower()
        or COURSE_NAME_MATCH in (c.get('course_code') or '').lower()
    ]
    if not courses:
        console.print(f'[red]No course matching "{COURSE_NAME_MATCH}" found among your TA/teacher courses.[/red]')
        sys.exit(1)
    if len(courses) == 1:
        return courses[0]

    console.print(f'[yellow]Multiple courses match "{COURSE_NAME_MATCH}":[/yellow]\n')
    for i, c in enumerate(courses, 1):
        console.print(f'  {i}. {c.get("name")}  [dim]({c.get("course_code")})[/dim]')
    choice = console.input('\nWhich one? [number]: ').strip()
    return courses[int(choice) - 1]


def main():
    apply_changes = '--apply' in sys.argv

    base_url = os.getenv('CANVAS_URL')
    token = os.getenv('CANVAS_TOKEN')
    if not base_url or not token:
        console.print('[red]Missing CANVAS_URL / CANVAS_TOKEN in .env[/red]')
        sys.exit(1)

    api = CanvasAPI(base_url, token)

    course = pick_course(api)
    course_id = course['id']
    console.print(f'\n[cyan]Course:[/cyan] {course.get("name")}  [dim](id {course_id})[/dim]')

    tz = resolve_timezone(api)
    target_local = datetime(TARGET_YEAR, TARGET_MONTH, TARGET_DAY, TARGET_HOUR, TARGET_MINUTE, tzinfo=tz)
    target_utc_iso = target_local.astimezone(ZoneInfo('UTC')).isoformat().replace('+00:00', 'Z')
    console.print(
        f'[cyan]Target Until date:[/cyan] {target_local.strftime("%b %d, %Y %I:%M %p")} '
        f'({tz.key})  [dim]→ {target_utc_iso} UTC[/dim]\n'
    )

    console.print('[dim]Fetching modules…[/dim]')
    modules = api.get_modules(course_id)
    assignment_module: dict = {}
    for m in modules:
        for item in api.get_module_items(course_id, m['id']):
            if item.get('type') == 'Assignment' and item.get('content_id'):
                assignment_module[item['content_id']] = m.get('name', '')

    console.print('[dim]Fetching assignments…[/dim]\n')
    assignments = api.get_assignments_with_overrides(course_id)

    def in_skip_module(a):
        return bool(SKIP_MODULE_RE.search(assignment_module.get(a['id'], '')))

    to_update = [a for a in assignments if not in_skip_module(a)]
    skipped = [a for a in assignments if in_skip_module(a)]

    t = Table(box=box.ROUNDED, header_style='bold cyan', show_lines=False)
    t.add_column('Assignment', min_width=32)
    t.add_column('Module', min_width=16)
    t.add_column('Current Until', min_width=18)
    t.add_column('New Until', min_width=18)
    t.add_column('Action', min_width=10)

    has_overrides = []
    for a in assignments:
        mod = assignment_module.get(a['id']) or '[dim]—[/dim]'
        current = fmt_dt(a.get('lock_at'), tz)
        skip = in_skip_module(a)
        new_val = '[dim]unchanged[/dim]' if skip else fmt_dt(target_utc_iso, tz)
        action = '[yellow]SKIP (W07)[/yellow]' if skip else '[green]UPDATE[/green]'
        t.add_row(a['name'], mod, current, new_val, action)
        if not skip and a.get('overrides'):
            has_overrides.append(a['name'])

    console.print(t)
    console.print(
        f'\n[bold green]{len(to_update)}[/bold green] assignments will be updated  '
        f'[bold yellow]{len(skipped)}[/bold yellow] skipped (W07 module)\n'
    )

    if has_overrides:
        console.print(
            '[yellow]Note:[/yellow] the following assignments being updated have section/student '
            'date overrides. This only changes the assignment\'s base Until date — any override with '
            'its own Until date will NOT be touched and may still differ:'
        )
        for name in has_overrides:
            console.print(f'  • {name}')
        console.print()

    if not apply_changes:
        console.print('[dim]Dry run only — no changes made. Re-run with --apply to actually update Canvas.[/dim]')
        return

    console.print('[bold red]Applying changes to live Canvas now…[/bold red]\n')
    errors = []
    for a in to_update:
        try:
            api.update_assignment(course_id, a['id'], lock_at=target_utc_iso)
            console.print(f'[green]✓[/green] {a["name"]}')
        except Exception as e:
            errors.append((a['name'], str(e)))
            console.print(f'[red]✗[/red] {a["name"]}: {e}')

    console.print(f'\n[bold]{len(to_update) - len(errors)}[/bold] updated successfully.')
    if errors:
        console.print(f'[red]{len(errors)} failed:[/red]')
        for name, err in errors:
            console.print(f'  - {name}: {err}')


if __name__ == '__main__':
    main()
