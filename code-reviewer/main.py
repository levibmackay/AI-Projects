import sys
import typer
from pathlib import Path
from rich.console import Console

app = typer.Typer(
    help="AI Code Reviewer. Paste code, get expert feedback powered by Groq, Gemini, or Ollama.",
    no_args_is_help=True,
)
console = Console()


@app.command("review")
def review_cmd(
    filepath: str = typer.Argument(None, help="Path to file to review (optional, or paste code interactively)"),
    mode: str = typer.Option("full", "--mode", "-m", help="Review mode: full, quick, security, performance, roast"),
    language: str = typer.Option(None, "--lang", "-l", help="Override language detection"),
    agent: str = typer.Option("auto", "--agent", "-a", help="Provider: auto, groq, gemini, ollama"),
    multi: bool = typer.Option(False, "--multi", help="Run all available models and merge results"),
    chat: bool = typer.Option(False, "--chat", "-c", help="Drop into chat mode after the review"),
):
    """Review code from a file or pasted input."""
    from reviewers.code_reviewer import review as do_review, ChatSession
    from ui.display import show_review, show_multi_review, show_code, prompt_code_input, chat_prompt, show_chat_response

    if filepath:
        path = Path(filepath)
        if not path.exists():
            console.print(f"[red]File not found: {filepath}[/red]")
            raise typer.Exit(1)
        code = path.read_text()
        lang = language or None
        source = filepath
    elif not sys.stdin.isatty():
        code = sys.stdin.read()
        lang = language
        source = "stdin"
    else:
        code = prompt_code_input()
        lang = language
        source = "paste"

    if not code.strip():
        console.print("[red]No code provided.[/red]")
        raise typer.Exit(1)

    detected_lang = lang or "unknown"
    console.print(f"\n[dim]Source: {source}  |  Mode: {mode}  |  Agent: {agent}[/dim]")

    with console.status("[cyan]Reviewing your code...[/cyan]"):
        try:
            result = do_review(
                code=code,
                mode=mode,
                language=lang,
                agent_name=agent,
                filepath=filepath,
                multi_model=multi,
            )
        except Exception as e:
            console.print(f"[red]Review failed: {e}[/red]")
            raise typer.Exit(1)

    if multi and "individual_reviews" in result:
        show_multi_review(result)
    else:
        show_review(result)

    if chat:
        _run_chat(code, result["review"], result["language"], agent)


@app.command("chat")
def chat_cmd(
    filepath: str = typer.Argument(None, help="File to load (or paste interactively)"),
    agent: str = typer.Option("auto", "--agent", "-a"),
):
    """Interactively chat about your code with an AI after an initial review."""
    from reviewers.code_reviewer import review as do_review, ChatSession
    from ui.display import show_review, prompt_code_input, chat_prompt, show_chat_response

    if filepath:
        code = Path(filepath).read_text()
    elif not sys.stdin.isatty():
        code = sys.stdin.read()
    else:
        code = prompt_code_input()

    if not code.strip():
        console.print("[red]No code provided.[/red]")
        raise typer.Exit(1)

    with console.status("[cyan]Running initial review...[/cyan]"):
        try:
            result = do_review(code=code, mode="full", agent_name=agent, filepath=filepath)
        except Exception as e:
            console.print(f"[red]Review failed: {e}[/red]")
            raise typer.Exit(1)

    show_review(result)
    _run_chat(code, result["review"], result["language"], agent)


def _run_chat(code: str, initial_review: str, language: str, agent_name: str):
    from reviewers.code_reviewer import ChatSession
    from ui.display import chat_prompt, show_chat_response

    session = ChatSession(code, initial_review, language, agent_name)
    console.print("\n[bold cyan]Chat mode[/bold cyan] [dim]— ask anything about your code. Type 'exit' to quit.[/dim]\n")

    turn = 1
    while True:
        try:
            question = chat_prompt(turn)
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Exiting chat.[/dim]")
            break

        if question.strip().lower() in ("exit", "quit", "q", "bye"):
            console.print("[dim]Exiting chat.[/dim]")
            break

        if not question.strip():
            continue

        with console.status("[cyan]Thinking...[/cyan]"):
            try:
                response = session.ask(question)
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                continue

        show_chat_response(response, session.agent.name)
        turn += 1


@app.command("quick")
def quick_cmd(
    filepath: str = typer.Argument(None),
    agent: str = typer.Option("auto", "--agent", "-a"),
):
    """Fast one-shot review: top 3 issues, under 200 words."""
    from reviewers.code_reviewer import review as do_review
    from ui.display import show_review, prompt_code_input

    if filepath:
        code = Path(filepath).read_text()
    elif not sys.stdin.isatty():
        code = sys.stdin.read()
    else:
        code = prompt_code_input()

    with console.status("[cyan]Quick review...[/cyan]"):
        result = do_review(code=code, mode="quick", agent_name=agent, filepath=filepath)
    show_review(result)


@app.command("security")
def security_cmd(
    filepath: str = typer.Argument(None),
    agent: str = typer.Option("auto", "--agent", "-a"),
):
    """Deep security audit: injection, XSS, auth issues, secrets, and more."""
    from reviewers.code_reviewer import review as do_review
    from ui.display import show_review, prompt_code_input

    if filepath:
        code = Path(filepath).read_text()
    elif not sys.stdin.isatty():
        code = sys.stdin.read()
    else:
        code = prompt_code_input()

    with console.status("[cyan]Running security audit...[/cyan]"):
        result = do_review(code=code, mode="security", agent_name=agent, filepath=filepath)
    show_review(result)


@app.command("roast")
def roast_cmd(
    filepath: str = typer.Argument(None),
    agent: str = typer.Option("auto", "--agent", "-a"),
):
    """Get your code brutally roasted. Every jab comes with a real fix."""
    from reviewers.code_reviewer import review as do_review
    from ui.display import show_review, prompt_code_input

    if filepath:
        code = Path(filepath).read_text()
    elif not sys.stdin.isatty():
        code = sys.stdin.read()
    else:
        code = prompt_code_input()

    with console.status("[cyan]Preparing roast...[/cyan]"):
        result = do_review(code=code, mode="roast", agent_name=agent, filepath=filepath)
    show_review(result)


@app.command("history")
def history_cmd(
    limit: int = typer.Option(10, "--limit", "-n"),
    show_id: str = typer.Option(None, "--show", "-s", help="Show full review by ID"),
):
    """Browse your past code reviews."""
    from utils.history import get_history, get_review
    from ui.display import show_history

    if show_id:
        review = get_review(show_id)
        if review:
            from rich.markdown import Markdown
            console.print(Markdown(review))
        else:
            console.print(f"[red]Review '{show_id}' not found.[/red]")
        return

    show_history(get_history(limit))


@app.command("providers")
def providers_cmd():
    """Show which AI providers are configured and available."""
    from agents.router import get_all_available
    from ui.display import show_providers

    agents = get_all_available()
    show_providers(agents)
    if not agents:
        console.print("\n[yellow]No providers configured. Copy .env.template to .env and add your API keys.[/yellow]")


if __name__ == "__main__":
    app()
