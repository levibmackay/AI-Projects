from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from scrapers.byui_scraper import Section

console = Console()


def _rmp_str(rmp: dict | None) -> str:
    if not rmp:
        return "[dim]No rating[/dim]"
    rating = rmp.get("rating")
    if not rating:
        return "[dim]No rating[/dim]"
    r = float(rating)
    color = "green" if r >= 4.0 else "yellow" if r >= 3.0 else "red"
    wta = rmp.get("would_take_again")
    wta_str = f"  {wta:.0f}% again" if wta else ""
    return f"[{color}]{r:.1f}/5.0[/{color}][dim]{wta_str}[/dim]"


def _days_str(days: list) -> str:
    return "".join(days) if days else "TBA"


def _time_str(start: str | None, end: str | None) -> str:
    if not start:
        return "TBA"
    if end:
        return f"{start} – {end}"
    return start


def show_sections(course: str, sections: list[Section], morning_only: bool, no_friday: bool):
    filters = []
    if morning_only:
        filters.append("morning only")
    if no_friday:
        filters.append("no Friday")
    filter_note = f"  [dim]({', '.join(filters)})[/dim]" if filters else ""

    if not sections:
        console.print(f"\n[yellow]No sections found for [bold]{course}[/bold] matching your filters.[/yellow]")
        console.print("[dim]Try --any-time or --allow-friday to see more results.[/dim]\n")
        return

    table = Table(
        title=f"{course} — Available Sections{filter_note}",
        box=box.ROUNDED,
        show_lines=True,
        title_style="bold cyan",
    )
    table.add_column("Sec", style="dim", width=5)
    table.add_column("Title", style="bold", max_width=28)
    table.add_column("Professor", max_width=22)
    table.add_column("RMP", justify="center", min_width=14)
    table.add_column("Days", justify="center", width=6)
    table.add_column("Time", min_width=18)
    table.add_column("Seats", justify="center", width=6)
    table.add_column("CRN", style="dim", width=7)

    for s in sections:
        seats_str = str(s.seats_available) if s.seats_available else "[dim]?[/dim]"
        table.add_row(
            s.section_num or "—",
            s.title or s.course_code,
            s.professor,
            _rmp_str(s.rmp),
            _days_str(s.days),
            _time_str(s.start_time, s.end_time),
            seats_str,
            s.crn or "—",
        )

    console.print()
    console.print(table)
    console.print()


def show_plan(plan: dict[str, list[Section]], term: str):
    console.print(Panel(f"[bold cyan]BYUI Class Plan — {term}[/bold cyan]", expand=False))

    if not plan:
        console.print("[green]No remaining courses to plan![/green]")
        return

    for course_code, sections in plan.items():
        if not sections:
            console.print(f"\n[yellow]{course_code}[/yellow] — [dim]No matching sections found[/dim]")
            continue

        best = sections[0]
        rmp_display = _rmp_str(best.rmp)
        console.print(
            f"\n[bold green]{course_code}[/bold green] "
            f"[dim]— best pick:[/dim] "
            f"[bold]{best.professor}[/bold] "
            f"{rmp_display}  "
            f"[cyan]{_days_str(best.days)} {_time_str(best.start_time, best.end_time)}[/cyan]  "
            f"CRN: [bold]{best.crn or '—'}[/bold]"
        )

        if len(sections) > 1:
            for s in sections[1:3]:
                console.print(
                    f"  [dim]alt:[/dim] {s.professor}  {_rmp_str(s.rmp)}  "
                    f"{_days_str(s.days)} {_time_str(s.start_time, s.end_time)}  CRN: {s.crn or '—'}"
                )

    console.print()


def show_remaining(courses: list[str]):
    if not courses:
        console.print("[green]All required courses are complete![/green]")
        return
    console.print(Panel(f"[bold]Remaining Required Courses[/bold]", expand=False))
    for c in courses:
        console.print(f"  • {c}")
    console.print()
