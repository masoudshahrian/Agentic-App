"""Command-line interface (Typer + Rich)."""
from __future__ import annotations

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.config import ConfigError
from app.graph import AgentState, build_graph
from app.main import create_llm, run_request

app = typer.Typer(add_completion=False, help="Multi-skill AI agent: summarize, translate, calculate, chat.")
console = Console()

EXIT_WORDS = {"exit", "quit", "q", "خروج"}


def _show(state: AgentState, verbose: bool) -> None:
    skills = " + ".join(state.selected_skills) or "none"
    mode = ""
    if len(state.selected_skills) == 2:
        mode = " (sequential)" if state.depends_on_previous else " (parallel)"
    console.print(f"[bold cyan]Skills:[/] {skills}{mode}   [bold cyan]Language:[/] {state.detected_language}")
    if verbose:
        table = Table(show_header=False, box=None)
        table.add_row("discovery", f"{state.discovery_strategy}: {len(state.candidate_skills)} of "
                                   f"{state.registered_skill_count} skills shortlisted")
        table.add_row("routing context", f"{state.routing_context_chars} chars (~{state.routing_context_chars // 4} tokens, approx.)")
        table.add_row("confidence", str(state.routing_confidence))
        table.add_row("routing source", state.routing_source)
        table.add_row("reason", state.reasoning_summary)
        for note in state.routing_notes:
            table.add_row("note", note)
        console.print(table)
    title = ("Clarification needed" if state.clarification_required
             else "Unsupported request" if state.unsupported_request else "Answer")
    console.print(Panel(state.final_response or "", title=title, border_style="yellow" if state.unsupported_request else "green"))
    for error in state.errors:
        console.print(f"[yellow]warning:[/] {error}")


def _handle(graph, prompt: str, verbose: bool) -> None:
    with console.status("Thinking..."):
        state = run_request(graph, prompt)
    _show(state, verbose)


@app.command()
def main(
    prompt: Optional[str] = typer.Argument(None, help="A single request. Omit it to start interactive mode."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show routing confidence, source and notes."),
) -> None:
    """Run one request, or start an interactive session (each line is an independent request)."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        graph = build_graph(create_llm())
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/] {exc}")
        raise typer.Exit(code=2) from None

    if prompt is not None:
        _handle(graph, prompt, verbose)
        return

    console.print(Panel(
        "Ask me to [b]summarize[/], [b]translate[/], [b]calculate[/] or just chat — in English or Persian.\n"
        "Each request is independent (no memory). Type [b]exit[/] to quit.",
        title="I4Twins multi-skill agent", border_style="cyan",
    ))
    while True:
        try:
            line = console.input("[bold]you> [/]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nBye!")
            return
        if line.lower() in EXIT_WORDS:
            console.print("Bye!")
            return
        if not line:
            console.print("[yellow]Please type a request.[/]")
            continue
        try:
            _handle(graph, line, verbose)
        except Exception as exc:  # keep the session alive on unexpected errors
            console.print(f"[red]Unexpected error:[/] {type(exc).__name__}: {exc}")
