import re
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()


def _score_color(text: str) -> str:
    m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", text)
    if not m:
        return "white"
    score = float(m.group(1))
    if score >= 8:
        return "green"
    if score >= 6:
        return "yellow"
    if score >= 4:
        return "orange3"
    return "red"


def show_review(result: dict):
    review = result["review"]
    lang = result["language"]
    agent = result["agent"]
    mode = result["mode"]

    color = _score_color(review)

    console.print()
    console.print(Panel(
        Markdown(review),
        title=f"[bold {color}] Code Review[/bold {color}]",
        subtitle=f"[dim]{agent}  |  mode: {mode}  |  language: {lang}[/dim]",
        border_style=color,
        padding=(1, 2),
    ))
    console.print(f"[dim]Saved to: {result['saved']}[/dim]\n")


def show_multi_review(result: dict):
    if "individual_reviews" in result:
        for r in result["individual_reviews"]:
            console.print(Panel(Markdown(r), border_style="dim", padding=(0, 1)))
    show_review(result)


def show_history(entries: list):
    if not entries:
        console.print("[yellow]No review history yet.[/yellow]")
        return

    table = Table(title="Review History", box=box.ROUNDED, show_lines=True)
    table.add_column("ID", style="dim", max_width=24)
    table.add_column("Date", style="cyan", width=19)
    table.add_column("Lang", width=10)
    table.add_column("Mode", width=10)
    table.add_column("Model", max_width=22)
    table.add_column("Preview", max_width=50)

    for e in entries:
        table.add_row(
            e["id"][-20:],
            e["date"][:19],
            e["language"],
            e["mode"],
            e["agent"],
            e["preview"],
        )
    console.print(table)


def show_code(code: str, language: str):
    console.print(Panel(
        Syntax(code, language, theme="monokai", line_numbers=True),
        title=f"[bold]{language}[/bold]",
        border_style="dim",
    ))


def prompt_code_input() -> str:
    console.print(Panel(
        "[bold cyan]Paste your code below.[/bold cyan]\n"
        "[dim]When done, press Enter then Ctrl+D (Linux/Mac) or Ctrl+Z + Enter (Windows).[/dim]",
        border_style="cyan",
    ))
    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass
    return "\n".join(lines)


def chat_prompt(session_num: int) -> str:
    return console.input(f"[bold cyan]You[/bold cyan] [dim]({session_num})[/dim]: ")


def show_chat_response(response: str, agent: str):
    console.print(Panel(
        Markdown(response),
        title=f"[bold green]{agent}[/bold green]",
        border_style="green",
        padding=(0, 1),
    ))


def show_providers(agents: list):
    table = Table(title="Available AI Providers", box=box.SIMPLE)
    table.add_column("Provider", style="bold")
    table.add_column("Status")
    table.add_column("Notes")

    provider_info = {
        "Groq": ("Free tier, very fast, Llama 3.3 70B", "green"),
        "Gemini": ("Free tier, 1500 req/day, Gemini 1.5 Flash", "blue"),
        "Ollama": ("Local, completely unlimited", "yellow"),
    }

    active_names = {a.name for a in agents}
    for name, (note, color) in provider_info.items():
        active = any(name.lower() in a.lower() for a in active_names)
        status = f"[{color}]Active[/{color}]" if active else "[dim]Not configured[/dim]"
        table.add_row(name, status, note)

    console.print(table)
