"""CLI entrypoint for Codebase Intelligent Assistant using Typer and Rich."""

import asyncio
from pathlib import Path
from typing import Optional
import typer
import uvicorn
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from src.agent.orchestrator import AgentOrchestrator
from src.agent.state import AgentState, ChatMessage
from src.analysis.repo_diff import RepoDiffAnalyzer
from src.config import settings
from src.indexing.delta_indexer import DeltaIndexer
from src.indexing.repo_map import RepoMapGenerator

cli_app = typer.Typer(
    name="codebase-agent",
    help="Codebase Intelligent Assistant - Private, local agentic code assistant",
    add_completion=False,
)
console = Console()


@cli_app.command()
def serve(
    host: str = typer.Option(settings.server_host, help="Server host"),
    port: int = typer.Option(settings.server_port, help="Server port"),
) -> None:
    """Starts the FastAPI Web Studio backend server."""
    console.print(
        Panel(
            f"[bold green]Starting Codebase Assistant Web Studio[/bold green]\n"
            f"URL: [cyan]http://{host}:{port}[/cyan]\n"
            f"Model: [yellow]{settings.llm_model}[/yellow] via {settings.llm_provider}\n"
            f"Workspace: {settings.workspace_dir}",
            title="Codebase Assistant Server",
            border_style="blue",
        )
    )
    uvicorn.run("src.server.app:app", host=host, port=port, reload=False)


@cli_app.command()
def popup() -> None:
    """Launches the floating native desktop pop-up assistant."""
    from src.ui.popup import launch_popup

    console.print("[bold cyan]Launching native floating pop-up window...[/bold cyan]")
    launch_popup()


@cli_app.command()
def index() -> None:
    """Scans and updates the AST cache and hybrid index for the workspace."""
    console.print("[bold yellow]Scanning workspace for incremental updates...[/bold yellow]")
    indexer = DeltaIndexer(settings.workspace_dir, settings.cache_db_path)
    added, modified, deleted = indexer.scan_changes()

    table = Table(title="Delta Indexer Scan Summary", border_style="blue")
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Files")

    table.add_row("Added", str(len(added)), ", ".join(added[:5]) + ("..." if len(added) > 5 else ""))
    table.add_row("Modified", str(len(modified)), ", ".join(modified[:5]) + ("..." if len(modified) > 5 else ""))
    table.add_row("Deleted", str(len(deleted)), ", ".join(deleted[:5]) + ("..." if len(deleted) > 5 else ""))
    console.print(table)

    # Process additions and modifications
    total_chunks = 0
    for rel_path in added + modified:
        res = indexer.index_file(rel_path)
        if res:
            parsed, chunks = res
            total_chunks += len(chunks)

    for rel_path in deleted:
        indexer.remove_file(rel_path)

    console.print(f"[bold green][OK] Indexing complete![/bold green] Processed {total_chunks} code chunks.")


@cli_app.command(name="map")
def show_repo_map(
    budget: int = typer.Option(1500, help="Maximum token budget for repository outline"),
) -> None:
    """Displays the PageRank-ranked repository map."""
    generator = RepoMapGenerator(settings.workspace_dir, max_tokens=budget)
    repo_map = generator.generate_map()
    console.print(Panel(repo_map, title="AST PageRank Repository Map", border_style="cyan"))


@cli_app.command()
def status() -> None:
    """Shows the Git status of the repository."""
    orchestrator = AgentOrchestrator()
    git_status = orchestrator.git.get_status()

    table = Table(title=f"Git Status (Branch: {git_status.current_branch})", border_style="green")
    table.add_column("State", style="bold")
    table.add_column("Files")

    table.add_row("Modified", ", ".join(git_status.modified) or "None")
    table.add_row("Staged", ", ".join(git_status.staged) or "None")
    table.add_row("Untracked", ", ".join(git_status.untracked) or "None")
    console.print(table)


@cli_app.command()
def diff(
    base: str = typer.Option("HEAD", help="Base commit or branch to compare against"),
) -> None:
    """Performs an AST-level comparison against a base commit."""
    analyzer = RepoDiffAnalyzer(settings.workspace_dir)
    comp = analyzer.compare_working_tree_against_commit(base)

    console.print(f"[bold]Comparing working tree against {base}:[/bold]")
    if not comp.added_symbols and not comp.modified_symbols and not comp.removed_symbols:
        console.print("[dim]No AST symbol changes detected.[/dim]")
        return

    table = Table(title="AST Semantic Diff", border_style="magenta")
    table.add_column("Type", style="bold")
    table.add_column("File")
    table.add_column("Symbol")
    table.add_column("Details")

    for s in comp.added_symbols:
        table.add_row("[green]+ Added[/green]", s.file_path, s.symbol_name, s.details)
    for s in comp.modified_symbols:
        table.add_row("[yellow]~ Modified[/yellow]", s.file_path, s.symbol_name, s.details)
    for s in comp.removed_symbols:
        table.add_row("[red]- Removed[/red]", s.file_path, s.symbol_name, s.details)

    console.print(table)


@cli_app.command()
def chat() -> None:
    """Starts an interactive terminal chat session with the assistant."""
    console.print(
        Panel(
            "[bold green]Starting interactive chat session with Codebase Assistant.[/bold green]\n"
            "Type your question or request. Type [bold red]'exit'[/bold red] to quit.",
            border_style="blue",
        )
    )
    orchestrator = AgentOrchestrator()
    state = AgentState()

    async def _chat_loop() -> None:
        while True:
            try:
                user_input = console.input("\n[bold cyan]You > [/bold cyan]").strip()
                if not user_input or user_input.lower() in ("exit", "quit"):
                    break

                state.messages.append(ChatMessage(role="user", content=user_input))
                with console.status("[bold green]Agent reasoning & inspecting code...[/bold green]"):
                    resp = await orchestrator.step(state)

                if resp.tool_calls:
                    for tc in resp.tool_calls:
                        console.print(f"[dim]>> Executed tool: [bold]{tc.name}[/bold][/dim]")

                console.print(Panel(Markdown(resp.content), title="Assistant", border_style="green"))

                if state.pending_patches:
                    for pid, p in list(state.pending_patches.items()):
                        console.print(
                            Panel(
                                f"[yellow]Proposed Patch for {p.file_path}:[/yellow]\n{p.diff}",
                                title=f"Pending Patch: {pid}",
                                border_style="yellow",
                            )
                        )
                        confirm = console.input(f"Apply patch {pid}? (y/n): ").strip().lower()
                        if confirm == "y":
                            orchestrator.apply_pending_patch(state, pid)
                            console.print("[green][OK] Patch applied successfully![/green]")
                        else:
                            del state.pending_patches[pid]
                            console.print("[red]Patch discarded.[/red]")

            except (KeyboardInterrupt, EOFError):
                break

    asyncio.run(_chat_loop())


def main() -> None:
    """Main CLI entrypoint."""
    cli_app()


if __name__ == "__main__":
    main()
