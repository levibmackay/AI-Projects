#!/usr/bin/env python3
"""Canvas TA Tool — grade and assignment checkup helper"""

import curses
import html
import os
import re
import statistics
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
    # AI-risk analysis cache (populated lazily, cleared on refresh since it's a new CourseData)
    ai_content: Dict[Tuple, Dict] = field(default_factory=dict)     # (user_id, asn_id) -> extracted content
    ai_stats: Dict[Tuple, Optional[Dict]] = field(default_factory=dict)  # (user_id, asn_id) -> analyzer stats
    ai_analysis: Optional[Dict[int, List[Dict]]] = None             # user_id -> risk entries


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


# ─── AI usage detection (heuristic) ─────────────────────────────────────────
#
# This is NOT a reliable AI detector — there is no such thing. It combines a
# few weak, easily-gamed signals (stock LLM phrasing/comments, unusually
# uniform structure, a sudden style shift from the student's own past work,
# and grade jumps) into a rough 0-100 "worth a second look" score. Baselines
# only ever look at a student's PRIOR submissions (in due-date order) so a
# student isn't flagged just for turning in their first couple assignments
# before there's any history to compare against. Treat this as a triage hint,
# never as evidence on its own.

MIN_WORDS_FOR_TEXT_ANALYSIS = 40
MIN_CODE_LINES_FOR_ANALYSIS = 8
MIN_PRIOR_SAMPLES = 3   # need this many prior data points before trusting a baseline

# Only assignments whose name matches this pattern are analyzed. This course
# uses a weekly Learn/Prove structure and only the "Prove" submissions are
# worth checking — adjust this pattern if your course names things differently.
PROVE_ASSIGNMENT_RE = re.compile(r'\bprove\b', re.IGNORECASE)


def is_prove_assignment(assignment: Dict) -> bool:
    return bool(PROVE_ASSIGNMENT_RE.search(assignment.get('name') or ''))

AI_PHRASES = [
    'as an ai language model', 'as an ai model', 'i am an ai',
    "i don't have personal experiences", 'i do not have personal experiences',
    'in conclusion', 'in summary', 'to summarize', 'overall,',
    'furthermore,', 'moreover,', 'additionally,', 'it is important to note',
    "it's important to note", 'it is worth noting', 'delve into', 'delving into',
    'navigate the complexities', "in today's society", "in today's world",
    'plays a crucial role', 'plays a vital role', 'in the realm of',
    'a testament to', 'ever-evolving', 'ever-changing landscape',
    'in the digital age', 'paradigm shift', 'cutting-edge', 'unprecedented',
    'multifaceted', 'underscores the importance', 'underscore the importance',
    'this highlights', 'holistic approach', 'robust understanding',
    'foster a deeper understanding', 'shed light on', 'vibrant tapestry',
    'tapestry of', 'myriad of', 'a myriad', 'seamless integration',
    'garner attention', 'garnered attention', 'stands as a',
    'serves as a testament', 'plethora of', 'invaluable insight',
    'invaluable insights', 'on the other hand,',
]

AI_CODE_MARKERS = [
    'step 1', 'step 2', 'step 3', 'step 4', 'initialize', 'example usage',
    'this function', 'helper function', 'driver code', 'in this example',
    'main function', "let's", 'first, we', 'next, we', 'finally, we',
    'here we', 'now we', 'define the', 'this class represents',
    'for demonstration purposes', 'sample usage', 'test the function',
]

# Line-comment prefix per language, used to measure comment density and to
# find comments worth flagging. Defaults to '#' for unrecognized languages.
COMMENT_PREFIX = {
    'python': '#', 'ruby': '#',
    'java': '//', 'javascript': '//', 'typescript': '//', 'c': '//', 'cpp': '//',
    'csharp': '//', 'go': '//', 'rust': '//', 'kotlin': '//', 'swift': '//', 'php': '//',
}

CODE_EXTENSIONS = {
    '.py': 'python', '.java': 'java', '.js': 'javascript', '.jsx': 'javascript',
    '.ts': 'typescript', '.tsx': 'typescript', '.c': 'c', '.h': 'c',
    '.cpp': 'cpp', '.cc': 'cpp', '.hpp': 'cpp', '.cs': 'csharp',
    '.rb': 'ruby', '.go': 'go', '.php': 'php', '.swift': 'swift',
    '.kt': 'kotlin', '.rs': 'rust',
}
TEXT_EXTENSIONS = {'.txt', '.md'}

CONTRACTION_RE = re.compile(r"\b\w+'(t|re|ve|ll|d|m)\b")
WORD_RE = re.compile(r"[A-Za-z']+")
TAG_RE = re.compile(r'<[^>]+>')


def get_submission_content(api: CanvasAPI, sub: Dict) -> Dict:
    """Extract previewable text from a submission: the text-entry body, or all
    text-decodable file attachments (source code, .txt, .md) — students often
    turn in more than one file, so every matching attachment is fetched and
    combined rather than stopping at the first. Binary formats like PDF/DOCX/
    images are skipped — there's no reliable extraction without extra
    dependencies, so those show up as "no text to analyze"."""
    body = sub.get('body')
    if body and WORD_RE.search(body):
        return {'text': html.unescape(TAG_RE.sub(' ', body)), 'kind': 'prose', 'filename': None, 'lang': None}

    files: List[Tuple[str, str, Optional[str]]] = []  # (filename, text, lang)
    for att in (sub.get('attachments') or []):
        filename = att.get('filename') or att.get('display_name') or 'file'
        ext = os.path.splitext(filename)[1].lower()
        url = att.get('url')
        if not url or (ext not in CODE_EXTENSIONS and ext not in TEXT_EXTENSIONS):
            continue
        text = api.fetch_text(url)
        if text:
            files.append((filename, text, CODE_EXTENSIONS.get(ext)))

    if not files:
        return {'text': None, 'kind': 'none', 'filename': None, 'lang': None}

    if len(files) == 1:
        filename, text, lang = files[0]
        return {'text': text, 'kind': 'code' if lang else 'prose', 'filename': filename, 'lang': lang}

    # Multiple files: keep every one, clearly separated, so both the analyzer
    # and the preview screen see the full submission rather than just the first file.
    combined = '\n\n'.join(f'# ===== {fname} =====\n{text}' for fname, text, _ in files)
    langs = [lang for _, _, lang in files if lang]
    return {
        'text': combined,
        'kind': 'code' if langs else 'prose',
        'filename': ', '.join(fname for fname, _, _ in files),
        'lang': statistics.mode(langs) if langs else None,
    }


def analyze_prose(text: str) -> Optional[Dict]:
    words = WORD_RE.findall(text)
    if len(words) < MIN_WORDS_FOR_TEXT_ANALYSIS:
        return None

    sentences = [s for s in re.split(r'[.!?]+', text) if s.strip()]
    sentence_lens = [n for n in (len(WORD_RE.findall(s)) for s in sentences) if n > 0]

    word_count = len(words)
    contraction_hits = len(CONTRACTION_RE.findall(text.lower()))

    phrase_hits = 0
    flagged_lines = []
    for i, line in enumerate(text.splitlines() or [text], start=1):
        hits = [p for p in AI_PHRASES if p in line.lower()]
        if hits:
            phrase_hits += len(hits)
            flagged_lines.append((i, line.strip(), f'Contains stock phrase "{hits[0]}"'))

    avg_sentence_len = statistics.mean(sentence_lens) if sentence_lens else 0
    sentence_cv = (
        statistics.stdev(sentence_lens) / avg_sentence_len
        if len(sentence_lens) >= 3 and avg_sentence_len else None
    )
    structural = max(0.0, min(1.0, 1 - sentence_cv / 0.7)) if sentence_cv is not None else None

    return {
        'kind': 'prose',
        'primary_hits': phrase_hits,
        'primary_rate': phrase_hits / word_count * 100,
        'primary_label': 'stock AI phrase(s) (e.g. "furthermore", "delve into", "in conclusion")',
        'structural': structural,
        'structural_label': 'Unusually uniform sentence lengths',
        'baseline_features': {
            'avg_sentence_len': avg_sentence_len,
            'contraction_rate': contraction_hits / word_count * 100,
            'phrase_rate': phrase_hits / word_count * 100,
        },
        'flagged_lines': flagged_lines,
    }


def analyze_code(text: str, lang: Optional[str]) -> Optional[Dict]:
    lines = text.splitlines()
    non_blank = [l for l in lines if l.strip()]
    if len(non_blank) < MIN_CODE_LINES_FOR_ANALYSIS:
        return None

    prefix = COMMENT_PREFIX.get(lang, '#')
    comment_lines = [l for l in non_blank if l.strip().startswith(prefix)]

    marker_hits = 0
    flagged_lines = []
    for i, line in enumerate(lines, start=1):
        if not line.strip().startswith(prefix):
            continue
        hits = [m for m in AI_CODE_MARKERS if m in line.lower()]
        if hits:
            marker_hits += len(hits)
            flagged_lines.append((i, line.strip(), f'AI-style comment pattern ("{hits[0]}")'))

    comment_ratio = len(comment_lines) / len(non_blank)
    avg_line_len = statistics.mean(len(l) for l in non_blank)

    return {
        'kind': 'code',
        'primary_hits': marker_hits,
        'primary_rate': marker_hits / len(non_blank) * 100,
        'primary_label': 'AI-style code comment(s) (e.g. "step 1", "helper function", "example usage")',
        'structural': max(0.0, min(1.0, (comment_ratio - 0.15) / 0.35)),
        'structural_label': f'Heavily commented code ({comment_ratio:.0%} of lines are comments)',
        'baseline_features': {
            'comment_ratio': comment_ratio,
            'avg_line_len': avg_line_len,
            'marker_rate': marker_hits / len(non_blank) * 100,
        },
        'flagged_lines': flagged_lines,
    }


def analyze_content(content: Dict) -> Optional[Dict]:
    text = content.get('text')
    if not text:
        return None
    if content['kind'] == 'code':
        return analyze_code(text, content.get('lang'))
    return analyze_prose(text)


def score_submission(
    stat: Optional[Dict],
    prior_stats: List[Dict],
    grade_pct: Optional[float],
    avg_prior_pct: Optional[float],
) -> Optional[Tuple[int, List[str], str]]:
    """Combine available signals into (risk 0-100, reasons, confidence). None if nothing to go on.

    `prior_stats` and `avg_prior_pct` must only reflect submissions BEFORE this
    one (in due-date order) — comparing against later work as well as earlier
    work is what caused early assignments to get flagged for "jumping" above
    an average that was really just pulled down by harder work later on.
    """
    if stat is None and avg_prior_pct is None:
        return None

    score = 0.0
    reasons: List[str] = []
    signals = 0

    if stat is not None:
        signals += 1
        rate_cap = 3.0 if stat['kind'] == 'prose' else 5.0
        primary_norm = min(stat['primary_rate'] / rate_cap, 1.0)
        if stat['primary_hits'] > 0:
            score += primary_norm * 30
            if primary_norm > 0.3:
                reasons.append(f"{stat['primary_hits']} {stat['primary_label']}")

        if stat.get('structural'):
            score += stat['structural'] * 15
            if stat['structural'] > 0.55:
                reasons.append(stat['structural_label'])

        same_kind_prior = [s for s in prior_stats if s['kind'] == stat['kind']]
        if len(same_kind_prior) >= MIN_PRIOR_SAMPLES:
            signals += 1
            invert_keys = {'contraction_rate'}
            z_scores = []
            for key in stat['baseline_features']:
                vals = [s['baseline_features'][key] for s in same_kind_prior if key in s['baseline_features']]
                if len(vals) < MIN_PRIOR_SAMPLES:
                    continue
                mean = statistics.mean(vals)
                sd = statistics.pstdev(vals) or 1.0
                z = (stat['baseline_features'][key] - mean) / sd
                z_scores.append(max(-z if key in invert_keys else z, 0.0))
            if z_scores:
                dev_norm = max(0.0, min(1.0, statistics.mean(z_scores) / 2.0))
                score += dev_norm * 35
                if dev_norm > 0.4:
                    reasons.append("Writing/coding style shifts sharply from this student's earlier submissions")
    else:
        reasons.append('No extractable submission text (unsupported file type) — based on grade pattern only')

    if grade_pct is not None and avg_prior_pct is not None:
        signals += 1
        jump_norm = max(0.0, min(1.0, (grade_pct - avg_prior_pct) / 40.0))
        score += jump_norm * 20
        if jump_norm > 0.4:
            reasons.append(f"Score jumped from this student's prior average ({avg_prior_pct:.0f}%) to {grade_pct:.0f}%")

    confidence = 'high' if signals >= 3 else 'medium' if signals == 2 else 'low'
    return round(min(score, 100)), reasons, confidence


def compute_ai_analysis(api: CanvasAPI, data: CourseData) -> Dict[int, List[Dict]]:
    """Per-student list of {assignment, score, reasons, confidence, content, stat}.

    Cached on `data` so the list view, student lookup, and preview screen all
    share one pass (and one set of attachment downloads) until the next refresh.
    """
    if data.ai_analysis is not None:
        return data.ai_analysis

    prove_assignments = [a for a in data.assignments if is_prove_assignment(a)]

    grade_pcts: Dict[Tuple[int, int], float] = {}
    for (sid, aid), sub in data.sub_map.items():
        a = data.assignment_map.get(aid)
        possible = a.get('points_possible') if a else None
        score = sub.get('score')
        if score is not None and possible:
            grade_pcts[(sid, aid)] = score / possible * 100

    per_student: Dict[int, List[Dict]] = {}
    for student in data.students:
        sid = student['id']
        entries: List[Dict] = []
        prior_grade_pcts: List[float] = []
        prior_stats: List[Dict] = []

        # data.assignments is already ordered by due_at (see CanvasAPI.get_assignments),
        # so walking the Prove assignments in order gives us a chronological
        # "prior work" baseline built only from that same weekly Prove cadence.
        for a in prove_assignments:
            aid = a['id']
            sub = data.sub_map.get((sid, aid))
            if sub is None or sub.get('workflow_state') in (None, 'unsubmitted', 'deleted'):
                continue

            key = (sid, aid)
            if key not in data.ai_content:
                data.ai_content[key] = get_submission_content(api, sub)
            content = data.ai_content[key]

            if key not in data.ai_stats:
                data.ai_stats[key] = analyze_content(content)
            stat = data.ai_stats[key]

            grade_pct = grade_pcts.get(key)
            avg_prior_pct = statistics.mean(prior_grade_pcts) if len(prior_grade_pcts) >= MIN_PRIOR_SAMPLES else None

            result = score_submission(stat, prior_stats, grade_pct, avg_prior_pct)
            if result is not None:
                risk, reasons, confidence = result
                entries.append({
                    'assignment': a,
                    'score': risk,
                    'reasons': reasons,
                    'confidence': confidence,
                    'content': content,
                    'stat': stat,
                })

            # Update history AFTER scoring, so this submission never leaks into its own baseline.
            if grade_pct is not None:
                prior_grade_pcts.append(grade_pct)
            if stat is not None:
                prior_stats.append(stat)

        per_student[sid] = entries

    data.ai_analysis = per_student
    return per_student


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


def view_missing_by_assignment(data: CourseData):
    console.print()
    console.rule('[bold]Missing Submissions by Assignment[/bold]')

    asns = gradable(data)
    past = [a for a in asns if parse_dt(a.get('due_at')) and parse_dt(a['due_at']) < NOW]

    if not past:
        console.print('\n[yellow]No past-due gradable assignments found.[/yellow]')
        Prompt.ask('\nPress Enter to return')
        return

    total_students = len(data.students)
    rows = []
    for a in past:
        missing_students = []
        for student in data.students:
            sub = data.sub_map.get((student['id'], a['id']))
            if is_missing(sub, True):
                missing_students.append(student.get('sortable_name') or student['name'])
        if missing_students:
            rows.append((a, sorted(missing_students)))

    if not rows:
        console.print('\n[green]No missing submissions on any past-due assignment![/green]')
        Prompt.ask('\nPress Enter to return')
        return

    rows.sort(key=lambda r: len(r[1]), reverse=True)

    total_missing = sum(len(names) for _, names in rows)
    console.print(
        f'\n[bold red]{total_missing}[/bold red] missing submissions across '
        f'[bold]{len(rows)}[/bold] assignments\n'
    )

    t = Table(box=box.ROUNDED, header_style='bold cyan', show_lines=False)
    t.add_column('Assignment',       min_width=32)
    t.add_column('Due',              min_width=10)
    t.add_column('Missing', justify='center', min_width=8)
    t.add_column('% of Class', justify='right', min_width=10)
    t.add_column('Students Missing', min_width=40)

    for a, names in rows:
        due = parse_dt(a.get('due_at'))
        due_str = due.strftime('%b %d') if due else '—'
        pct = len(names) / total_students * 100 if total_students else 0
        pct_color = 'red' if pct >= 25 else 'yellow' if pct >= 10 else 'dim'

        preview = ', '.join(names[:4])
        if len(names) > 4:
            preview += f' [dim](+{len(names)-4} more)[/dim]'

        t.add_row(
            a['name'],
            due_str,
            f'[red]{len(names)}[/red]',
            f'[{pct_color}]{pct:.0f}%[/{pct_color}]',
            preview,
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


AI_DISCLAIMER = (
    "[dim]Heuristic estimate based on stock AI phrasing/comments, structural uniformity,\n"
    "a shift from the student's own prior submissions, and grade jumps (baselines only\n"
    "use work turned in earlier, so early assignments aren't flagged for lack of history).\n"
    "Only weekly \"Prove\" assignments are analyzed. Not proof of AI use — a prompt to\n"
    "take a closer look, not a verdict.[/dim]"
)


def view_ai_risk_list(api: CanvasAPI, data: CourseData):
    console.print()
    console.rule('[bold]AI Usage Risk — All Students[/bold]')
    console.print(f'\n{AI_DISCLAIMER}\n')

    with console.status('[bold cyan]Analyzing Prove submissions…'):
        analysis = compute_ai_analysis(api, data)

    rows = []
    for student in data.students:
        entries = analysis.get(student['id'], [])
        if not entries:
            continue
        top = max(entries, key=lambda e: e['score'])
        flagged = [e for e in entries if e['score'] >= 50]
        rows.append((student, top, flagged))

    if not rows:
        console.print('[yellow]Not enough Prove assignment submissions to analyze yet.[/yellow]')
        Prompt.ask('\nPress Enter to return')
        return

    rows.sort(key=lambda r: r[1]['score'], reverse=True)

    high = sum(1 for _, top, _ in rows if top['score'] >= 70)
    moderate = sum(1 for _, top, _ in rows if 50 <= top['score'] < 70)
    console.print(
        f'[bold red]{high}[/bold red] high-risk  '
        f'[bold yellow]{moderate}[/bold yellow] moderate-risk  '
        f'[dim]out of {len(rows)} students with analyzable submissions[/dim]\n'
    )

    t = Table(box=box.ROUNDED, header_style='bold cyan', show_lines=False)
    t.add_column('Student',                    min_width=22)
    t.add_column('Risk',    justify='right',    min_width=6)
    t.add_column('Flagged', justify='center',   min_width=8)
    t.add_column('Most Suspicious Assignment',  min_width=26)
    t.add_column('Why',                         min_width=40)

    for student, top, flagged in rows:
        name = student.get('sortable_name') or student['name']
        color = 'red' if top['score'] >= 70 else 'yellow' if top['score'] >= 50 else 'dim'
        reason_preview = '; '.join(top['reasons'][:2]) or '[dim]—[/dim]'

        t.add_row(
            name,
            f'[{color}]{top["score"]}%[/{color}]',
            f'[red]{len(flagged)}[/red]' if flagged else '[dim]0[/dim]',
            top['assignment']['name'],
            reason_preview,
        )

    console.print(t)
    Prompt.ask('\nPress Enter to return')


def _draw_code_pager(stdscr, entries: List[Dict], index: int, student_name: str):
    curses.curs_set(0)
    stdscr.keypad(True)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_RED)   # flagged line
    curses.init_pair(2, curses.COLOR_CYAN, -1)                  # header
    curses.init_pair(3, curses.COLOR_RED, -1)                   # high risk
    curses.init_pair(4, curses.COLOR_YELLOW, -1)                # moderate risk

    top = 0
    while True:
        entry = entries[index]
        a = entry['assignment']
        content = entry['content']
        stat = entry['stat']
        risk = entry['score']
        text = content.get('text')
        lines = text.splitlines() if text else [
            '(no extractable text for this submission — unsupported file type or empty)'
        ]
        flagged = {ln: reason for ln, _, reason in (stat.get('flagged_lines') if stat else [])}

        height, width = stdscr.getmaxyx()
        body_height = max(1, height - 3)
        max_top = max(0, len(lines) - body_height)
        top = max(0, min(top, max_top))

        stdscr.erase()

        risk_attr = curses.color_pair(3) if risk >= 70 else curses.color_pair(4) if risk >= 50 else 0
        header = f' {student_name} — {a["name"]}  [{index + 1}/{len(entries)}]'
        stdscr.addnstr(0, 0, header, width - 1, curses.A_BOLD | curses.color_pair(2))

        stats_line = f' Risk: {risk}%  Confidence: {entry["confidence"]}'
        if content.get('filename'):
            stats_line += f'   File: {content["filename"]}'
        stdscr.addnstr(1, 0, stats_line, width - 1, curses.A_BOLD | risk_attr)

        for row in range(body_height):
            li = top + row
            if li >= len(lines):
                break
            is_flag = (li + 1) in flagged
            suffix = f'  <- {flagged[li + 1]}' if is_flag else ''
            display = f'{li + 1:>5} {lines[li]}{suffix}'.replace('\t', '    ')
            attr = (curses.color_pair(1) | curses.A_BOLD) if is_flag else 0
            try:
                stdscr.addnstr(2 + row, 0, display[:width - 1], width - 1, attr)
            except curses.error:
                pass

        footer = ' ↑/↓ j/k scroll   space/b page   g/G top/bottom   e next Prove   q prev Prove   Esc back '
        try:
            stdscr.addnstr(height - 1, 0, footer[:width - 1], width - 1, curses.A_REVERSE)
        except curses.error:
            pass

        stdscr.refresh()
        key = stdscr.getch()

        if key == 27:  # Esc
            return
        elif key == ord('e'):
            index = (index + 1) % len(entries)
            top = 0
        elif key == ord('q'):
            index = (index - 1) % len(entries)
            top = 0
        elif key in (curses.KEY_DOWN, ord('j')):
            top += 1
        elif key in (curses.KEY_UP, ord('k')):
            top -= 1
        elif key in (curses.KEY_NPAGE, ord(' '), ord('f')):
            top += body_height
        elif key in (curses.KEY_PPAGE, ord('b')):
            top -= body_height
        elif key in (ord('g'), curses.KEY_HOME):
            top = 0
        elif key in (ord('G'), curses.KEY_END):
            top = max_top


def view_submission_pager(entries: List[Dict], start_index: int, student_name: str):
    """Full-screen scrollable code viewer. e/q flip between a student's Prove
    submissions, arrows/j/k/space/b scroll, Esc returns — no Enter needed."""
    curses.wrapper(_draw_code_pager, entries, start_index, student_name)


def view_ai_risk_detail(api: CanvasAPI, data: CourseData):
    console.print()
    console.rule('[bold]AI Usage Risk — Student Lookup[/bold]')

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

    with console.status('[bold cyan]Analyzing Prove submissions…'):
        analysis = compute_ai_analysis(api, data)

    entries = sorted(analysis.get(sid, []), key=lambda e: e['score'], reverse=True)

    console.print()
    if not entries:
        console.print(Panel(
            f'[bold white]{name}[/bold white]\n\n[dim]No Prove submissions with enough data to analyze.[/dim]',
            title='[cyan]AI Usage Risk[/cyan]',
            border_style='cyan',
            expand=False,
            padding=(0, 2),
        ))
        Prompt.ask('\nPress Enter to return')
        return

    top_score = entries[0]['score']
    overall_color = 'red' if top_score >= 70 else 'yellow' if top_score >= 50 else 'green'
    console.print(Panel(
        f'[bold white]{name}[/bold white]\n\n'
        f'Highest risk: [{overall_color}]{top_score}%[/{overall_color}]  '
        f'[dim]({entries[0]["assignment"]["name"]})[/dim]',
        title='[cyan]AI Usage Risk[/cyan]',
        border_style='cyan',
        expand=False,
        padding=(0, 2),
    ))
    console.print(f'\n{AI_DISCLAIMER}\n')

    t = Table(box=box.ROUNDED, header_style='bold cyan', show_lines=True)
    t.add_column('#',                     justify='right', min_width=3)
    t.add_column('Assignment',            min_width=26)
    t.add_column('Risk',       justify='right', min_width=6)
    t.add_column('Confidence',            min_width=10)
    t.add_column('Signals',               min_width=45)

    for i, e in enumerate(entries, start=1):
        color = 'red' if e['score'] >= 70 else 'yellow' if e['score'] >= 50 else 'dim'
        t.add_row(
            str(i),
            e['assignment']['name'],
            f'[{color}]{e["score"]}%[/{color}]',
            e['confidence'],
            '\n'.join(f'• {r}' for r in e['reasons']) or '[dim]No signals triggered[/dim]',
        )

    console.print(t)

    valid = [str(i) for i in range(1, len(entries) + 1)]
    console.print()
    choice = Prompt.ask(
        'Enter a # to open the code viewer ([dim]then e/q flip between Prove submissions, '
        'arrows/space scroll, Esc returns here[/dim]), or press Enter to return',
        default='', show_default=False,
    )
    if choice in valid:
        view_submission_pager(entries, int(choice) - 1, name)
    elif choice:
        console.print('[red]Invalid choice.[/red]')


# ─── Navigation ──────────────────────────────────────────────────────────────

def run_submenu(title: str, items: List[Tuple[str, str]], actions: Dict[str, callable]):
    """IVR-style submenu: print numbered options plus a "0. Back", run the
    chosen action, and keep re-showing the submenu until the user backs out."""
    while True:
        console.print()
        console.rule(f'[bold cyan]{title}[/bold cyan]')
        console.print()
        for key, label in items:
            console.print(f'  [cyan]{key}.[/cyan]  {label}')
        console.print('  [cyan]0.[/cyan]  Back')
        console.print()

        choice = Prompt.ask('Choice', choices=[key for key, _ in items] + ['0'])
        if choice == '0':
            return
        actions[choice]()



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

        console.print('  [cyan]1.[/cyan]  Missing & Late Work')
        console.print('  [cyan]2.[/cyan]  Grading')
        console.print('  [cyan]3.[/cyan]  Student Lookup')
        console.print('  [cyan]4.[/cyan]  AI Usage Risk  [dim](all students)[/dim]')
        console.print('  [cyan]5.[/cyan]  Refresh Data')
        console.print('  [cyan]6.[/cyan]  Switch Course')
        console.print('  [cyan]0.[/cyan]  Exit')
        console.print()

        choice = Prompt.ask('Choice', choices=['0', '1', '2', '3', '4', '5', '6'])

        if choice == '1':
            run_submenu('Missing & Late Work', [
                ('1', 'Missing Assignments  [dim](by student)[/dim]'),
                ('2', 'Missing Submissions  [dim](by assignment)[/dim]'),
            ], {
                '1': lambda: view_missing_assignments(data),
                '2': lambda: view_missing_by_assignment(data),
            })
        elif choice == '2':
            run_submenu('Grading', [
                ('1', 'Ungraded Submissions'),
                ('2', 'Grade Analysis  [dim](what\'s keeping students from an A)[/dim]'),
            ], {
                '1': lambda: view_ungraded(data),
                '2': lambda: view_grade_analysis(data),
            })
        elif choice == '3':
            run_submenu('Student Lookup', [
                ('1', 'Grades & Assignments'),
                ('2', 'AI Usage Risk'),
            ], {
                '1': lambda: view_student_detail(data),
                '2': lambda: view_ai_risk_detail(api, data),
            })
        elif choice == '4':
            view_ai_risk_list(api, data)
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
