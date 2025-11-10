"""Statistics command for usage analytics."""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from analytics import get_usage_tracker

console = Console()


@click.command()
@click.option('--days', '-d', default=30, help='Number of days to analyze (default: 30)')
def stats(days):
    """
    Display usage statistics.

    Examples:
        snipvault stats
        snipvault stats --days 7
    """
    try:
        console.print(f"\n[bold cyan]SnipVault Usage Statistics (Last {days} days)[/bold cyan]\n")

        tracker = get_usage_tracker()
        summary = tracker.get_summary_report(days)

        # Overview
        overview_table = Table(show_header=False, box=None, padding=(0, 2))
        overview_table.add_column("Metric", style="yellow")
        overview_table.add_column("Value", style="bold white")

        overview_table.add_row("Total Events", str(summary['total_events']))

        for event_type, count in summary['event_breakdown'].items():
            overview_table.add_row(f"  {event_type.title()}", str(count))

        console.print(Panel(overview_table, title="[bold]Overview[/bold]", border_style="cyan"))
        console.print()

        # Search Statistics
        search_stats = summary['search_stats']

        if search_stats['total_searches'] > 0:
            search_table = Table(show_header=True, header_style="bold cyan")
            search_table.add_column("Metric", style="yellow")
            search_table.add_column("Value", style="white")

            search_table.add_row("Total Searches", str(search_stats['total_searches']))
            search_table.add_row("Unique Queries", str(search_stats['unique_queries']))
            search_table.add_row("Avg/Day", f"{search_stats['avg_searches_per_day']:.1f}")

            console.print(Panel(search_table, title="[bold]Search Activity[/bold]", border_style="green"))
            console.print()

            # Top queries
            if search_stats['top_queries']:
                console.print("[bold yellow]Top Search Queries:[/bold yellow]")
                for query, count in search_stats['top_queries'][:10]:
                    console.print(f"  {count:>3}x  {query}")
                console.print()

            # Top languages
            if search_stats['top_languages']:
                console.print("[bold yellow]Top Languages Searched:[/bold yellow]")
                for lang, count in search_stats['top_languages'][:5]:
                    console.print(f"  {count:>3}x  {lang}")
                console.print()

        # Snippet Statistics
        snippet_stats = summary['snippet_stats']

        if snippet_stats['total_views'] > 0:
            snippet_table = Table(show_header=True, header_style="bold cyan")
            snippet_table.add_column("Metric", style="yellow")
            snippet_table.add_column("Value", style="white")

            snippet_table.add_row("Total Views", str(snippet_stats['total_views']))
            snippet_table.add_row("Unique Viewed", str(snippet_stats['unique_snippets_viewed']))
            snippet_table.add_row("Added", str(snippet_stats['snippets_added']))
            snippet_table.add_row("Updated", str(snippet_stats['snippets_updated']))
            snippet_table.add_row("Deleted", str(snippet_stats['snippets_deleted']))

            console.print(Panel(snippet_table, title="[bold]Snippet Activity[/bold]", border_style="magenta"))
            console.print()

            # Most viewed snippets
            if snippet_stats['most_viewed_snippets']:
                console.print("[bold yellow]Most Viewed Snippets:[/bold yellow]")
                for snippet_id, count in snippet_stats['most_viewed_snippets'][:10]:
                    console.print(f"  {count:>3}x  Snippet #{snippet_id}")
                console.print()

        if summary['total_events'] == 0:
            console.print("[dim]No usage data available for the specified period.[/dim]\n")

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()
