import typer
from rich.console import Console

app = typer.Typer(help="BYUI Class Planner — find the best schedule for your remaining courses.")
console = Console()


@app.command("search")
def search_cmd(
    course: str = typer.Argument(..., help="Course code to search (e.g. 'CS 246')"),
    term: str = typer.Option("Fall Semester 2026", "--term", "-t", help="Semester to search"),
    morning_only: bool = typer.Option(True, "--morning/--any-time", help="Only show morning classes"),
    no_friday: bool = typer.Option(True, "--no-friday/--allow-friday", help="Exclude Friday classes"),
):
    """Search for sections of a course, ranked by professor rating."""
    from scrapers.byui_scraper import search_courses
    from scrapers.rmp import get_professor_rating
    from planner.schedule_optimizer import filter_sections
    from planner.professor_ranker import rank_sections
    from ui.display import show_sections

    with console.status(f"[cyan]Searching BYUI schedule for {course}...[/cyan]"):
        try:
            sections = search_courses(course_code=course, term=term)
        except Exception as e:
            console.print(f"[red]Error fetching course data: {e}[/red]")
            raise typer.Exit(1)

    if not sections:
        console.print(f"[yellow]No sections found for '{course}' in {term}.[/yellow]")
        raise typer.Exit()

    with console.status("[cyan]Fetching Rate My Professor ratings...[/cyan]"):
        for s in sections:
            if s.professor and s.professor != "TBA":
                s.rmp = get_professor_rating(s.professor)

    sections = filter_sections(sections, morning_only=morning_only, no_friday=no_friday)
    sections = rank_sections(sections)
    show_sections(course, sections, morning_only=morning_only, no_friday=no_friday)


@app.command("plan")
def plan_cmd(
    term: str = typer.Option("Fall Semester 2026", "--term", "-t", help="Semester to plan"),
    morning_only: bool = typer.Option(True, "--morning/--any-time"),
    no_friday: bool = typer.Option(True, "--no-friday/--allow-friday"),
):
    """Show the best section for every remaining required course."""
    from planner.course_filter import get_remaining_courses
    from scrapers.byui_scraper import search_courses
    from scrapers.rmp import get_professor_rating
    from planner.schedule_optimizer import filter_sections
    from planner.professor_ranker import rank_sections
    from ui.display import show_plan

    remaining = get_remaining_courses()
    if not remaining:
        console.print("[green]You have no remaining required courses![/green]")
        raise typer.Exit()

    plan = {}
    for course_code in remaining:
        with console.status(f"[cyan]Looking up {course_code}...[/cyan]"):
            try:
                sections = search_courses(course_code=course_code, term=term)
                for s in sections:
                    if s.professor and s.professor != "TBA":
                        s.rmp = get_professor_rating(s.professor)
                sections = filter_sections(sections, morning_only=morning_only, no_friday=no_friday)
                sections = rank_sections(sections)
                plan[course_code] = sections
            except Exception as e:
                console.print(f"[yellow]Warning: could not fetch {course_code}: {e}[/yellow]")
                plan[course_code] = []

    show_plan(plan, term=term)


@app.command("remaining")
def remaining_cmd():
    """List all remaining required courses from your degree plan."""
    from planner.course_filter import get_remaining_courses
    from ui.display import show_remaining
    show_remaining(get_remaining_courses())


@app.command("complete")
def complete_cmd(
    course: str = typer.Argument(..., help="Course code to mark as completed (e.g. 'CS 111')"),
):
    """Mark a course as completed so it's removed from your plan."""
    from planner.course_filter import mark_completed
    mark_completed(course)
    console.print(f"[green]Marked {course.upper()} as completed.[/green]")


if __name__ == "__main__":
    app()
