#!/usr/bin/env python3
"""Canvas TA Tool — grade and assignment checkup helper"""

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich import box

from canvas_api import CanvasAPI

load_dotenv()
console = Console()
NOW = datetime.now(timezone.utc)


# ─── Data model ──────────────────────────────────────────────────────────────

@dataclass
class CourseData:
    course: Dict
    students: List[Dict] = field(default_factory=list)
    assignments: List[Dict] = field(default_factory=list)
    submissions: List[Dict] = field(default_factory=list)
    enrollments: List[Dict] = field(default_factory=list)
    # Indexed lookups built after load
    student_map: Dict[int, Dict] = field(default_factory=dict)      # user_id -> student
    assignment_map: Dict[int, Dict] = field(default_factory=dict)   # assignment_id -> assignment
    sub_map: Dict[Tuple, Dict] = field(default_factory=dict)        # (user_id, asn_id) -> sub
    grade_map: Dict[int, Dict] = field(default_factory=dict)        # user_id -> grades dict


# ─── Helpers ─────────────────────────────────────────────────────────────────

def parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def grade_color(score: Optional[float]) -> str:
    if score is None:
        return 'dim'
    if score >= 90:
        return 'green'
    if score >= 80:
        return 'yellow'
    if score >= 70:
        return 'orange3'
    return 'red'


def fmt_grade(score: Optional[float]) -> str:
    if score is None:
        return '[dim]—[/dim]'
    c = grade_color(score)
    return f'[{c}]{score:.1f}%[/{c}]'


def fmt_score(score: Optional[float], possible: float) -> str:
    if score is None:
        return f'[red]—/{possible:.0f}[/red]'
    pct = score / possible * 100 if possible else 0
    c = grade_color(pct)
    return f'[{c}]{score:.0f}/{possible:.0f}[/{c}]'


def gradable(data: CourseData) -> List[Dict]:
    """Assignments that count toward the grade and have point values."""
    return [
        a for a in data.assignments
        if a.get('points_possible')
        and not a.get('omit_from_final_grade')
        and 'not_graded' not in a.get('submission_types', [])
    ]


def is_missing(sub: Optional[Dict], past_due: bool) -> bool:
    if sub is None:
        return past_due
    return sub.get('missing', False) or (
        past_due and sub.get('workflow_state') == 'unsubmitted'
    )


def is_needs_grading(sub: Optional[Dict]) -> bool:
    return sub is not None and sub.get('workflow_state') in ('submitted', 'pending_review')


# ─── Data loading ─────────────────────────────────────────────────────────────

def load_course_data(api: CanvasAPI, course: Dict) -> CourseData:
    cid = course['id']
    data = CourseData(course=course)

    steps = [
        ('students', 'Loading students…',     lambda: api.get_students(cid)),
        ('assignments', 'Loading assignments…', lambda: api.get_assignments(cid)),
        ('submissions', 'Loading submissions…', lambda: api.get_submissions(cid)),
        ('enrollments', 'Loading grades…',      lambda: api.get_enrollments(cid)),
    ]
    for attr, msg, fn in steps:
        with console.status(f'[bold cyan]{msg}'):
            setattr(data, attr, fn())

    data.student_map    = {s['id']: s for s in data.students}
    data.assignment_map = {a['id']: a for a in data.assignments}
    data.sub_map        = {(s['user_id'], s['assignment_id']): s for s in data.submissions}
    data.grade_map      = {e['user_id']: e.get('grades', {}) for e in data.enrollments}

    console.print(
        f'[green]✓[/green] [bold]{len(data.students)}[/bold] students  '
        f'[bold]{len(data.assignments)}[/bold] assignments  '
        f'[bold]{len(data.submissions)}[/bold] submissions loaded'
    )
    return data


# ─── Views ───────────────────────────────────────────────────────────────────

def view_missing_assignments(data: CourseData):
    console.print()
    console.rule('[bold]Missing & Late Assignments[/bold]')

    asns = gradable(data)
    past = [a for a in asns if parse_dt(a.get('due_at')) and parse_dt(a['due_at']) < NOW]

    rows = []
    for student in sorted(data.students, key=lambda s: s.get('sortable_name', s['name'])):
        sid = student['id']
        missing_names, late_names = [], []
        for a in past:
            sub = data.sub_map.get((sid, a['id']))
            if is_missing(sub, True):
                missing_names.append(a['name'])
            elif sub and sub.get('late'):
                late_names.append(a['name'])
        if missing_names or late_names:
            score = data.grade_map.get(sid, {}).get('current_score')
            rows.append((student, score, missing_names, late_names))

    if not rows:
        console.print('\n[green]No students have missing or late assignments![/green]')
        Prompt.ask('\nPress Enter to return')
        return

    rows.sort(key=lambda r: len(r[2]) + len(r[3]), reverse=True)

    caught_up = len(data.students) - len(rows)
    console.print(
        f'\n[bold red]{len(rows)}[/bold red] students have missing or late work  '
        f'[dim]({caught_up} caught up)[/dim]\n'
    )

    t = Table(box=box.ROUNDED, header_style='bold cyan', show_lines=False)
    t.add_column('Student',              min_width=22)
    t.add_column('Grade',  justify='right', min_width=8)
    t.add_column('Missing',justify='center', min_width=7)
    t.add_column('Late',   justify='center', min_width=6)
    t.add_column('Missing Assignments',  min_width=40)

    for student, score, missing, late in rows:
        name = student.get('sortable_name') or student['name']
        preview = ', '.join(missing[:3])
        if len(missing) > 3:
            preview += f' [dim](+{len(missing)-3} more)[/dim]'

        t.add_row(
            name,
            fmt_grade(score),
            f'[red]{len(missing)}[/red]'    if missing else '[dim]0[/dim]',
            f'[yellow]{len(late)}[/yellow]' if late    else '[dim]0[/dim]',
            f'[red]{preview}[/red]'         if preview else '[dim]—[/dim]',
        )

    console.print(t)
    Prompt.ask('\nPress Enter to return')


def view_ungraded(data: CourseData):
    console.print()
    console.rule('[bold]Needs Grading[/bold]')

    # Group ungraded submissions by assignment
    by_asn: Dict[int, List] = {}
    for sub in data.submissions:
        if is_needs_grading(sub):
            by_asn.setdefault(sub['assignment_id'], []).append(sub)

    if not by_asn:
        console.print('\n[green]Nothing needs grading — you\'re all caught up![/green]')
        Prompt.ask('\nPress Enter to return')
        return

    rows = []
    for aid, subs in by_asn.items():
        asn = data.assignment_map.get(aid) or (subs[0].get('assignment') or {})
        oldest = min(
            (parse_dt(s.get('submitted_at')) for s in subs if s.get('submitted_at')),
            default=None,
        )
        wait = (NOW - oldest).days if oldest else None
        rows.append((asn, subs, wait))

    rows.sort(key=lambda r: r[2] if r[2] is not None else -1, reverse=True)

    total = sum(len(r[1]) for r in rows)
    console.print(
        f'\n[bold yellow]{total}[/bold yellow] submissions need grading across '
        f'[bold]{len(rows)}[/bold] assignments\n'
    )

    t = Table(box=box.ROUNDED, header_style='bold cyan')
    t.add_column('Assignment',        min_width=32)
    t.add_column('Due',               min_width=10)
    t.add_column('Ungraded', justify='center', min_width=8)
    t.add_column('Oldest Submission', min_width=16)

    for asn, subs, wait in rows:
        due = parse_dt(asn.get('due_at'))
        due_str = due.strftime('%b %d') if due else '—'

        if wait is None:
            wait_str = '[dim]—[/dim]'
        elif wait > 7:
            wait_str = f'[red]{wait}d ago[/red]'
        elif wait > 3:
            wait_str = f'[yellow]{wait}d ago[/yellow]'
        else:
            wait_str = f'{wait}d ago'

        t.add_row(
            asn.get('name', f'Assignment {asn.get("id", "?")}'),
            due_str,
            f'[yellow]{len(subs)}[/yellow]',
            wait_str,
        )

    console.print(t)
    Prompt.ask('\nPress Enter to return')


def view_grade_analysis(data: CourseData):
    console.print()
    console.rule('[bold]Grade Analysis — A Blockers[/bold]')

    asns = gradable(data)
    total_pts = sum(a.get('points_possible', 0) for a in asns)

    if not total_pts:
        console.print('[yellow]No gradable assignments with point values found.[/yellow]')
        Prompt.ask('\nPress Enter to return')
        return

    A_THRESHOLD = 90.0
    rows = []

    for student in data.students:
        sid = student['id']
        current = data.grade_map.get(sid, {}).get('current_score')
        if current is None:
            continue

        losses = []
        for a in asns:
            possible = a.get('points_possible', 0)
            if not possible:
                continue
            sub = data.sub_map.get((sid, a['id']))
            due = parse_dt(a.get('due_at'))
            past = due and due < NOW

            if is_missing(sub, bool(past)):
                lost, reason = possible, 'missing'
            elif sub and sub.get('score') is not None:
                lost = possible - sub['score']
                reason = f'{sub["score"]:.0f}/{possible:.0f}'
            else:
                continue

            if lost > 0:
                losses.append((a['name'], lost, lost / total_pts * 100, reason))

        losses.sort(key=lambda x: x[1], reverse=True)
        rows.append((student, current, A_THRESHOLD - current, losses[:3]))

    below = [(s, c, g, l) for s, c, g, l in rows if c < A_THRESHOLD]
    below.sort(key=lambda r: r[2])  # Smallest gap to A first

    if not below:
        console.print(
            f'\n[green bold]All {len(rows)} students are at or above 90%![/green bold]'
        )
        Prompt.ask('\nPress Enter to return')
        return

    above_count = len(rows) - len(below)
    console.print(
        f'\n[bold]{len(below)}[/bold] students below an A  '
        f'[dim]({above_count} already have an A)[/dim]\n'
    )

    t = Table(box=box.ROUNDED, header_style='bold cyan', show_lines=True)
    t.add_column('Student',    min_width=22)
    t.add_column('Grade',      justify='right', min_width=8)
    t.add_column('Gap to A',   justify='right', min_width=9)
    t.add_column('Biggest Point Losses', min_width=52)

    for student, current, gap, losses in below:
        name = student.get('sortable_name') or student['name']
        gap_color = 'red' if gap > 10 else 'yellow' if gap > 5 else 'orange3'

        parts = []
        for aname, lost, pct, reason in losses:
            short = aname if len(aname) <= 22 else aname[:20] + '…'
            tag = '[red]missing[/red]' if reason == 'missing' else f'[dim]{reason}[/dim]'
            parts.append(f'{short}  {tag}  [red]-{pct:.1f}%[/red]')

        t.add_row(
            name,
            fmt_grade(current),
            f'[{gap_color}]{gap:.1f}%[/{gap_color}]',
            '\n'.join(parts) or '[dim]—[/dim]',
        )

    console.print(t)
    Prompt.ask('\nPress Enter to return')


def view_student_detail(data: CourseData):
    console.print()
    console.rule('[bold]Student Lookup[/bold]')

    query = Prompt.ask('Search by name').strip().lower()
    if not query:
        return

    matches = [
        s for s in data.students
        if query in (s.get('sortable_name') or s.get('name', '')).lower()
        or query in s.get('name', '').lower()
    ]

    if not matches:
        console.print(f'\n[red]No student found matching "{query}"[/red]')
        Prompt.ask('\nPress Enter to return')
        return

    if len(matches) == 1:
        student = matches[0]
    else:
        console.print(f'\nFound {len(matches)} students:\n')
        for i, s in enumerate(matches[:10], 1):
            console.print(f'  [cyan]{i}.[/cyan] {s.get("sortable_name") or s["name"]}')
        console.print()
        choice = Prompt.ask('Select', choices=[str(i) for i in range(1, min(len(matches), 10) + 1)])
        student = matches[int(choice) - 1]

    sid = student['id']
    name = student.get('sortable_name') or student['name']
    email = student.get('email', '—')
    grades = data.grade_map.get(sid, {})
    current = grades.get('current_score')
    letter = grades.get('current_grade', '')

    grade_display = fmt_grade(current)
    if letter:
        grade_display += f'  [dim]({letter})[/dim]'

    console.print()
    console.print(Panel(
        f'[bold white]{name}[/bold white]\n'
        f'[dim]{email}[/dim]\n\n'
        f'Current Grade: {grade_display}',
        title='[cyan]Student Detail[/cyan]',
        border_style='cyan',
        expand=False,
        padding=(0, 2),
    ))

    asns = gradable(data)
    missing_count = late_count = needs_grading_count = 0

    t = Table(box=box.SIMPLE_HEAD, header_style='bold cyan', show_lines=False)
    t.add_column('Assignment',           min_width=32)
    t.add_column('Due',                  min_width=10)
    t.add_column('Score',  justify='right', min_width=12)
    t.add_column('Status',               min_width=16)

    for a in asns:
        sub = data.sub_map.get((sid, a['id']))
        due = parse_dt(a.get('due_at'))
        due_str = due.strftime('%b %d') if due else '—'
        possible = a.get('points_possible', 0)
        past = due and due < NOW

        if is_missing(sub, bool(past)):
            score_str = f'[red]—/{possible:.0f}[/red]'
            status = '[red]Missing[/red]'
            missing_count += 1
        elif sub is None or sub.get('workflow_state') == 'unsubmitted':
            score_str = '[dim]—[/dim]'
            status = '[dim]Not yet due[/dim]'
        elif is_needs_grading(sub):
            score_str = '[yellow]Submitted[/yellow]'
            status = '[yellow]Needs grading[/yellow]'
            needs_grading_count += 1
        elif sub.get('workflow_state') == 'graded':
            score = sub.get('score')
            late = sub.get('late', False)
            score_str = fmt_score(score, possible) if score is not None else f'[dim]0/{possible:.0f}[/dim]'
            if late:
                status = '[orange3]Graded (late)[/orange3]'
                late_count += 1
            else:
                status = '[green]Graded[/green]'
        else:
            score_str = '[dim]—[/dim]'
            status = '[dim]—[/dim]'

        t.add_row(a['name'], due_str, score_str, status)

    console.print()
    console.print(
        f'  [red]Missing:[/red] {missing_count}   '
        f'[orange3]Late:[/orange3] {late_count}   '
        f'[yellow]Needs grading:[/yellow] {needs_grading_count}'
    )
    console.print()
    console.print(t)
    Prompt.ask('\nPress Enter to return')


# ─── Navigation ──────────────────────────────────────────────────────────────

def select_course(api: CanvasAPI) -> Optional[Dict]:
    with console.status('[cyan]Fetching your courses…'):
        courses = api.get_ta_courses()

    if not courses:
        console.print(Panel(
            '[red]No TA or teacher courses found.[/red]\n\n'
            'Check that your CANVAS_TOKEN has the right permissions\n'
            'and that you are enrolled as a TA or teacher.',
            border_style='red',
        ))
        return None

    console.print()
    console.rule('[bold cyan]Canvas TA Tool[/bold cyan]')
    console.print('\n[bold]Select a course:[/bold]\n')

    for i, c in enumerate(courses, 1):
        name = c.get('name', f'Course {c["id"]}')
        code = c.get('course_code', '')
        suffix = f' [dim]({code})[/dim]' if code else ''
        console.print(f'  [cyan]{i:>2}.[/cyan] {name}{suffix}')

    console.print()
    choice = Prompt.ask('Course number', choices=[str(i) for i in range(1, len(courses) + 1)])
    return courses[int(choice) - 1]


def main_menu(api: CanvasAPI, course: Dict) -> str:
    data = load_course_data(api, course)
    course_name = course.get('name', f'Course {course["id"]}')

    while True:
        console.print()
        console.rule(f'[bold cyan]{course_name}[/bold cyan]')

        # Quick stats for the header
        asns = gradable(data)
        past = [a for a in asns if parse_dt(a.get('due_at')) and parse_dt(a['due_at']) < NOW]

        missing_total = 0
        for s in data.students:
            for a in past:
                sub = data.sub_map.get((s['id'], a['id']))
                if is_missing(sub, True):
                    missing_total += 1

        ungraded_total = sum(1 for sub in data.submissions if is_needs_grading(sub))

        console.print(
            f'\n  [dim]Students:[/dim] {len(data.students)}   '
            f'[dim]Assignments:[/dim] {len(data.assignments)}   '
            f'[red]Missing submissions:[/red] {missing_total}   '
            f'[yellow]Needs grading:[/yellow] {ungraded_total}\n'
        )

        console.print('  [cyan]1.[/cyan]  Missing Assignments')
        console.print('  [cyan]2.[/cyan]  Ungraded Submissions')
        console.print('  [cyan]3.[/cyan]  Grade Analysis  [dim](what\'s keeping students from an A)[/dim]')
        console.print('  [cyan]4.[/cyan]  Student Lookup')
        console.print('  [cyan]5.[/cyan]  Refresh Data')
        console.print('  [cyan]6.[/cyan]  Switch Course')
        console.print('  [cyan]0.[/cyan]  Exit')
        console.print()

        choice = Prompt.ask('Choice', choices=['0', '1', '2', '3', '4', '5', '6'])

        if choice == '1':
            view_missing_assignments(data)
        elif choice == '2':
            view_ungraded(data)
        elif choice == '3':
            view_grade_analysis(data)
        elif choice == '4':
            view_student_detail(data)
        elif choice == '5':
            data = load_course_data(api, course)
        elif choice == '6':
            return 'switch'
        elif choice == '0':
            console.print('\n[dim]Goodbye![/dim]\n')
            sys.exit(0)


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    base_url = os.getenv('CANVAS_URL')
    token    = os.getenv('CANVAS_TOKEN')

    if not base_url or not token:
        console.print(Panel(
            '[red]Missing configuration![/red]\n\n'
            'Create a [cyan].env[/cyan] file in this directory with:\n\n'
            '  CANVAS_URL=https://your-school.instructure.com\n'
            '  CANVAS_TOKEN=your_api_token\n\n'
            'See [cyan].env.example[/cyan] for instructions on getting your token.',
            title='Canvas TA Tool',
            border_style='red',
            padding=(0, 2),
        ))
        sys.exit(1)

    api = CanvasAPI(base_url, token)

    try:
        while True:
            course = select_course(api)
            if not course:
                sys.exit(1)
            result = main_menu(api, course)
            if result != 'switch':
                break
    except KeyboardInterrupt:
        console.print('\n[dim]Interrupted. Goodbye![/dim]\n')
        sys.exit(0)
    except Exception as e:
        console.print(f'\n[bold red]Error:[/bold red] {e}')
        if os.getenv('DEBUG'):
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
