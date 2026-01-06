#!/usr/bin/env python3
"""
CLI script to check BeVigil enrichment status.

Usage:
    python scripts/check_status.py
    python scripts/check_status.py --detailed
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.config import config
from src.supabase_client import SupabaseClient


console = Console()


@click.command()
@click.option(
    "--detailed", "-d",
    is_flag=True,
    default=False,
    help="Show detailed breakdown including vulnerability stats"
)
def main(detailed: bool):
    """Check BeVigil enrichment status and statistics."""
    # Validate configuration
    missing = config.validate()
    if missing:
        console.print(f"[red]Missing configuration: {', '.join(missing)}[/red]")
        sys.exit(1)

    try:
        supabase = SupabaseClient()
    except Exception as e:
        console.print(f"[red]Failed to connect to Supabase: {e}[/red]")
        sys.exit(1)

    # Get stats
    stats = supabase.get_stats()

    # Main stats table
    table = Table(title="BeVigil Enrichment Status")
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Percentage", justify="right")

    total = stats.total_android_apps
    processed = stats.completed + stats.not_found + stats.no_credits

    def pct(n):
        return f"{(n / total * 100):.1f}%" if total > 0 else "0%"

    table.add_row("Total Android Apps", str(total), "100%")
    table.add_row("─" * 20, "─" * 8, "─" * 10)
    table.add_row("[green]Completed[/green]", str(stats.completed), pct(stats.completed))
    table.add_row("[yellow]Not Found[/yellow]", str(stats.not_found), pct(stats.not_found))
    table.add_row("[blue]Processing[/blue]", str(stats.processing), pct(stats.processing))
    table.add_row("[orange1]Pending[/orange1]", str(stats.pending), pct(stats.pending))
    table.add_row("[red]Failed[/red]", str(stats.failed), pct(stats.failed))
    table.add_row("[red]No Credits[/red]", str(stats.no_credits), pct(stats.no_credits))
    table.add_row("─" * 20, "─" * 8, "─" * 10)

    remaining = total - processed
    table.add_row("[bold]Remaining[/bold]", f"[bold]{remaining}[/bold]", f"[bold]{pct(remaining)}[/bold]")

    console.print(table)

    if detailed:
        _show_detailed_stats(supabase)


def _show_detailed_stats(supabase: SupabaseClient):
    """Show detailed vulnerability and asset statistics."""
    client = supabase._client

    # Vulnerability stats
    console.print("\n")
    vuln_result = client.table("bevigil_vulnerabilities").select(
        "severity, category"
    ).execute()

    if vuln_result.data:
        vuln_table = Table(title="Vulnerability Statistics")
        vuln_table.add_column("Category", style="cyan")
        vuln_table.add_column("High", justify="right", style="red")
        vuln_table.add_column("Medium", justify="right", style="yellow")
        vuln_table.add_column("Low", justify="right", style="green")
        vuln_table.add_column("Total", justify="right", style="bold")

        # Count by category and severity
        counts = {}
        for row in vuln_result.data:
            cat = row.get("category", "unknown")
            sev = row.get("severity", "info")
            if cat not in counts:
                counts[cat] = {"high": 0, "medium": 0, "low": 0, "info": 0, "critical": 0}
            if sev in counts[cat]:
                counts[cat][sev] += 1

        for cat, sevs in sorted(counts.items()):
            total = sum(sevs.values())
            high = sevs.get("high", 0) + sevs.get("critical", 0)
            vuln_table.add_row(
                cat,
                str(high),
                str(sevs.get("medium", 0)),
                str(sevs.get("low", 0) + sevs.get("info", 0)),
                str(total),
            )

        console.print(vuln_table)

    # Top CWEs
    cwe_result = client.table("bevigil_vulnerabilities").select(
        "cwe_id, cwe_name"
    ).not_.is_("cwe_id", "null").execute()

    if cwe_result.data:
        cwe_counts = {}
        for row in cwe_result.data:
            cwe_id = row.get("cwe_id")
            cwe_name = row.get("cwe_name", "Unknown")
            if cwe_id:
                key = f"CWE-{cwe_id}"
                if key not in cwe_counts:
                    cwe_counts[key] = {"name": cwe_name, "count": 0}
                cwe_counts[key]["count"] += 1

        if cwe_counts:
            console.print("\n")
            cwe_table = Table(title="Top CWE Issues")
            cwe_table.add_column("CWE ID", style="cyan")
            cwe_table.add_column("Name", style="white", max_width=50)
            cwe_table.add_column("Count", justify="right", style="yellow")

            sorted_cwes = sorted(cwe_counts.items(), key=lambda x: x[1]["count"], reverse=True)
            for cwe_id, data in sorted_cwes[:10]:
                cwe_table.add_row(cwe_id, data["name"], str(data["count"]))

            console.print(cwe_table)

    # Asset stats
    console.print("\n")
    asset_result = client.table("bevigil_enrichment").select(
        "host_count, url_count, s3_bucket_count, email_count, ip_address_count, firebase_url_count"
    ).eq("enrichment_status", "completed").execute()

    if asset_result.data:
        totals = {
            "Hosts": 0,
            "URLs": 0,
            "S3 Buckets": 0,
            "Emails": 0,
            "IP Addresses": 0,
            "Firebase URLs": 0,
        }

        for row in asset_result.data:
            totals["Hosts"] += row.get("host_count", 0) or 0
            totals["URLs"] += row.get("url_count", 0) or 0
            totals["S3 Buckets"] += row.get("s3_bucket_count", 0) or 0
            totals["Emails"] += row.get("email_count", 0) or 0
            totals["IP Addresses"] += row.get("ip_address_count", 0) or 0
            totals["Firebase URLs"] += row.get("firebase_url_count", 0) or 0

        asset_table = Table(title="Extracted Assets (Total)")
        asset_table.add_column("Asset Type", style="cyan")
        asset_table.add_column("Count", justify="right", style="green")

        for asset_type, count in totals.items():
            asset_table.add_row(asset_type, f"{count:,}")

        console.print(asset_table)


if __name__ == "__main__":
    main()
