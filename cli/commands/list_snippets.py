"""List command for displaying all snippets."""

import click
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from datetime import datetime
from db.queries import list_all_snippets

console = Console()


@click.command()
@click.option('--limit', '-l', default=50, help='Maximum number of snippets per page (default: 50)')
@click.option('--page', '-p', default=1, help='Page number for pagination (default: 1)')
@click.option('--verbose', '-v', is_flag=True, help='Show full code instead of preview')
def list_snippets(limit, page, verbose):
    """
    List all stored code snippets.

    Example:
        snipvault list
        snipvault list --limit 10
        snipvault list --verbose
    """
    try:
        console.print("\n[bold cyan]Fetching snippets...[/bold cyan]\n")

        # Get all snippets for total count
        all_snippets = list_all_snippets(limit=10000)  # High limit to get all

        if not all_snippets:
            console.print("[yellow]No snippets found.[/yellow]")
            console.print("\nAdd your first snippet with:")
            console.print("  snipvault add <title> <code> --lang <language>")
            return

        # Apply pagination
        from utils.pagination import Paginator, format_pagination_info, get_page_navigation

        paginator = Paginator(page_size=limit)
        paginated = paginator.paginate(all_snippets, page=page)

        console.print(f"[bold green]Found {paginated.total_items} snippet(s):[/bold green]")
        console.print(f"[dim]{format_pagination_info(paginated)}[/dim]\n")

        snippets = paginated.items

        if verbose:
            # Verbose mode: Show full code with syntax highlighting
            for snippet in snippets:
                # Format timestamp
                created = snippet['created_at']
                if isinstance(created, datetime):
                    created_str = created.strftime('%Y-%m-%d %H:%M')
                else:
                    created_str = str(created)

                # Build header
                header_parts = [
                    f"[bold]{snippet['title']}[/bold]",
                    f"[dim](ID: {snippet['id']})[/dim]",
                    f"[blue]{snippet['language']}[/blue]",
                    f"[dim]{created_str}[/dim]"
                ]

                if snippet.get('tags'):
                    tags_str = ", ".join(snippet['tags'])
                    header_parts.append(f"[magenta]{tags_str}[/magenta]")

                console.print(" • ".join(header_parts))

                # Show full code
                syntax = Syntax(
                    snippet['code'],
                    snippet['language'],
                    theme="monokai",
                    line_numbers=True
                )
                console.print(syntax)
                console.print("\n" + "─" * 80 + "\n")

        else:
            # Table mode: Show compact overview
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("ID", style="dim", width=6)
            table.add_column("Title", style="bold")
            table.add_column("Language", style="blue")
            table.add_column("Tags", style="magenta")
            table.add_column("Code Preview", style="dim")
            table.add_column("Created", style="dim")

            for snippet in snippets:
                # Format timestamp
                created = snippet['created_at']
                if isinstance(created, datetime):
                    created_str = created.strftime('%Y-%m-%d')
                else:
                    created_str = str(created)

                # Code preview (first 50 chars)
                code_preview = snippet['code'][:50]
                if len(snippet['code']) > 50:
                    code_preview += "..."

                # Tags
                tags_str = ", ".join(snippet.get('tags', []))
                if not tags_str:
                    tags_str = "-"

                table.add_row(
                    str(snippet['id']),
                    snippet['title'],
                    snippet['language'],
                    tags_str,
                    code_preview,
                    created_str
                )

            console.print(table)
            console.print(f"\n[dim]Tip: Use --verbose to see full code[/dim]")

        # Show pagination navigation
        nav = get_page_navigation(paginated)
        if nav:
            console.print(f"\n[dim]{nav}[/dim]")

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()
