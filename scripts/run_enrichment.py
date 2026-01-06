#!/usr/bin/env python3
"""
CLI script to run BeVigil app enrichment.

Usage:
    python scripts/run_enrichment.py --help
    python scripts/run_enrichment.py --limit 5
    python scripts/run_enrichment.py --category Games --limit 10
    python scripts/run_enrichment.py --dry-run
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich import print as rprint

from src.config import config
from src.supabase_client import SupabaseClient
from src.bevigil_client import BeVigilClient
from src.enrichment_service import EnrichmentService


console = Console()


@click.command()
@click.option(
    "--limit", "-l",
    type=int,
    default=None,
    help="Maximum number of apps to process (default: all pending)"
)
@click.option(
    "--category", "-c",
    type=str,
    default=None,
    help="Filter by app category (e.g., 'Games', 'Social')"
)
@click.option(
    "--app-name", "-a",
    type=str,
    default=None,
    help="Filter by app name (case-insensitive contains)"
)
@click.option(
    "--bundle-id", "-b",
    type=str,
    default=None,
    help="Filter by bundle ID (case-insensitive contains)"
)
@click.option(
    "--developer", "-d",
    type=str,
    default=None,
    help="Filter by developer name (case-insensitive contains)"
)
@click.option(
    "--include-failed", "-f",
    is_flag=True,
    default=False,
    help="Include previously failed apps for retry"
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be processed without making API calls"
)
@click.option(
    "--list-categories",
    is_flag=True,
    default=False,
    help="List available app categories and exit"
)
@click.option(
    "--list-developers",
    is_flag=True,
    default=False,
    help="List available developers and exit"
)
def main(
    limit: int,
    category: str,
    app_name: str,
    bundle_id: str,
    developer: str,
    include_failed: bool,
    dry_run: bool,
    list_categories: bool,
    list_developers: bool,
):
    """
    BeVigil App Enrichment CLI

    Enrich Android apps with security intelligence from BeVigil OSINT API.

    Examples:

        # Process 5 apps (good for testing)
        python scripts/run_enrichment.py --limit 5

        # Process all Games category apps
        python scripts/run_enrichment.py --category Games

        # Search by developer
        python scripts/run_enrichment.py --developer Google --limit 10

        # Dry run to see what would be processed
        python scripts/run_enrichment.py --dry-run --limit 20

        # Retry failed apps
        python scripts/run_enrichment.py --include-failed --limit 10
    """
    # Validate configuration
    missing = config.validate()
    if missing:
        console.print(f"[red]Missing configuration: {', '.join(missing)}[/red]")
        console.print("Please set these in your .env file")
        sys.exit(1)

    # Initialize Supabase client
    try:
        supabase = SupabaseClient()
    except Exception as e:
        console.print(f"[red]Failed to connect to Supabase: {e}[/red]")
        sys.exit(1)

    # Handle list commands
    if list_categories:
        categories = supabase.get_android_app_categories()
        console.print("\n[bold]Available Android App Categories:[/bold]")
        for cat in categories:
            console.print(f"  - {cat}")
        console.print(f"\n[dim]Total: {len(categories)} categories[/dim]")
        return

    if list_developers:
        developers = supabase.get_android_app_developers()
        console.print("\n[bold]Available Android App Developers:[/bold]")
        for dev in developers[:50]:  # Limit output
            console.print(f"  - {dev}")
        if len(developers) > 50:
            console.print(f"  ... and {len(developers) - 50} more")
        console.print(f"\n[dim]Total: {len(developers)} developers[/dim]")
        return

    # Show current stats
    stats = supabase.get_stats()
    _display_stats(stats)

    # Get pending apps with filters
    console.print("\n[bold]Fetching apps to process...[/bold]")

    apps = supabase.get_pending_apps(
        limit=limit,
        category=category,
        app_name_contains=app_name,
        bundle_id_contains=bundle_id,
        developer_contains=developer,
        include_failed=include_failed,
    )

    if not apps:
        console.print("[yellow]No apps found matching the criteria.[/yellow]")
        return

    # Display what will be processed
    _display_apps_to_process(apps, dry_run)

    # Calculate credit usage
    credits_needed = len(apps) * 2  # 2 API calls per app
    console.print(f"\n[bold]Estimated API credits needed: {credits_needed}[/bold]")

    if dry_run:
        console.print("\n[yellow]Dry run complete. No API calls were made.[/yellow]")
        return

    # Confirm before proceeding
    if not click.confirm(f"\nProceed with enriching {len(apps)} apps?"):
        console.print("[yellow]Aborted.[/yellow]")
        return

    # Run enrichment
    _run_enrichment(apps, supabase)


def _display_stats(stats):
    """Display current enrichment statistics."""
    table = Table(title="Current Enrichment Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right")

    table.add_row("Total Android Apps", str(stats.total_android_apps))
    table.add_row("─" * 20, "─" * 10)
    table.add_row("Completed", f"[green]{stats.completed}[/green]")
    table.add_row("Pending", f"[yellow]{stats.pending}[/yellow]")
    table.add_row("Processing", f"[blue]{stats.processing}[/blue]")
    table.add_row("Failed", f"[red]{stats.failed}[/red]")
    table.add_row("Not Found", f"[dim]{stats.not_found}[/dim]")
    table.add_row("No Credits", f"[red]{stats.no_credits}[/red]")

    remaining = stats.total_android_apps - stats.completed - stats.not_found - stats.no_credits
    table.add_row("─" * 20, "─" * 10)
    table.add_row("Remaining to Process", f"[bold]{remaining}[/bold]")

    console.print(table)


def _display_apps_to_process(apps, dry_run: bool):
    """Display apps that will be processed."""
    title = "Apps to Process (Dry Run)" if dry_run else "Apps to Process"
    table = Table(title=title)
    table.add_column("#", justify="right", style="dim")
    table.add_column("App Name", style="cyan", max_width=30)
    table.add_column("Bundle ID", style="green", max_width=40)
    table.add_column("Category", style="yellow")
    table.add_column("Developer", style="magenta", max_width=25)

    for i, app in enumerate(apps[:20], 1):  # Show max 20
        table.add_row(
            str(i),
            app.app_name or "N/A",
            app.bundle_id,
            app.category or "N/A",
            app.developer_name or "N/A",
        )

    if len(apps) > 20:
        table.add_row("...", f"... and {len(apps) - 20} more ...", "", "", "")

    console.print(table)
    console.print(f"\n[bold]Total apps to process: {len(apps)}[/bold]")


def _run_enrichment(apps, supabase: SupabaseClient):
    """Run the enrichment process with progress display."""
    # Initialize clients
    try:
        bevigil = BeVigilClient()
        service = EnrichmentService(bevigil_client=bevigil, supabase_client=supabase)
    except Exception as e:
        console.print(f"[red]Failed to initialize clients: {e}[/red]")
        return

    results = {
        "completed": 0,
        "not_found": 0,
        "failed": 0,
        "no_credits": 0,
    }

    console.print("\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Enriching apps...", total=len(apps))

        for app in apps:
            progress.update(
                task,
                description=f"Processing: {app.bundle_id[:40]}..."
            )

            def on_progress(msg: str):
                progress.console.print(f"  [dim]{msg}[/dim]")

            try:
                success, status = service.enrich_app(app, on_progress=on_progress)

                if status == "completed":
                    results["completed"] += 1
                    progress.console.print(f"  [green]✓ Completed[/green]")
                elif status == "not_found":
                    results["not_found"] += 1
                    progress.console.print(f"  [yellow]⊘ Not found in BeVigil[/yellow]")
                elif status == "no_credits":
                    results["no_credits"] += 1
                    progress.console.print(f"  [red]✗ No credits remaining - stopping[/red]")
                    break
                else:
                    results["failed"] += 1
                    progress.console.print(f"  [red]✗ Failed: {status}[/red]")

            except KeyboardInterrupt:
                progress.console.print("\n[yellow]Interrupted by user[/yellow]")
                break
            except Exception as e:
                results["failed"] += 1
                progress.console.print(f"  [red]✗ Error: {e}[/red]")

            progress.advance(task)

    # Close clients
    service.close()

    # Display results
    console.print("\n")
    _display_results(results)

    # Show updated stats
    console.print("\n[bold]Updated Status:[/bold]")
    updated_stats = supabase.get_stats()
    _display_stats(updated_stats)


def _display_results(results: dict):
    """Display enrichment results summary."""
    panel_content = f"""
[green]Completed:[/green] {results['completed']}
[yellow]Not Found:[/yellow] {results['not_found']}
[red]Failed:[/red] {results['failed']}
[red]No Credits:[/red] {results['no_credits']}

[bold]Total Processed:[/bold] {sum(results.values())}
"""

    console.print(Panel(panel_content, title="Enrichment Results", border_style="blue"))


if __name__ == "__main__":
    main()
