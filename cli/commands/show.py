"""Show command for displaying a single snippet."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from db.queries import get_snippet_by_id
from search.related import get_related_snippets

console = Console()


@click.command()
@click.argument('snippet_id', type=int)
@click.option('--copy', '-c', is_flag=True, help='Copy code to clipboard')
@click.option('--related', '-r', is_flag=True, default=True, help='Show related snippets (default: enabled)')
@click.option('--no-related', is_flag=True, help='Hide related snippets')
def show(snippet_id, copy, related, no_related):
    """
    Display a single snippet by ID with full details.

    Examples:
        snipvault show 5
        snipvault show 10 --copy
    """
    try:
        # Fetch snippet
        console.print(f"\n[bold cyan]Fetching snippet ID {snippet_id}...[/bold cyan]")
        snippet = get_snippet_by_id(snippet_id)

        if not snippet:
            console.print(f"[red]✗ Snippet with ID {snippet_id} not found[/red]")
            raise click.Abort()

        # Create metadata table
        metadata_table = Table(show_header=False, box=None, padding=(0, 2))
        metadata_table.add_column("Key", style="yellow")
        metadata_table.add_column("Value", style="white")

        metadata_table.add_row("ID", str(snippet['id']))
        metadata_table.add_row("Title", snippet['title'])
        metadata_table.add_row("Language", snippet['language'])
        if snippet['tags']:
            metadata_table.add_row("Tags", ', '.join(snippet['tags']))
        metadata_table.add_row("Created", str(snippet['created_at']))

        console.print("\n")
        console.print(metadata_table)

        # Display code with syntax highlighting
        console.print(f"\n[bold yellow]Code:[/bold yellow]")
        syntax = Syntax(
            snippet['code'],
            snippet['language'],
            theme="monokai",
            line_numbers=True,
            word_wrap=True
        )
        console.print(syntax)

        # Copy to clipboard if requested
        if copy:
            try:
                import pyperclip
                pyperclip.copy(snippet['code'])
                console.print("\n[green]✓ Code copied to clipboard![/green]")
            except ImportError:
                console.print("\n[yellow]⚠ pyperclip not installed. Install with: pip install pyperclip[/yellow]")
            except Exception as e:
                console.print(f"\n[yellow]⚠ Failed to copy to clipboard: {e}[/yellow]")

        # Show related snippets if enabled
        if related and not no_related:
            console.print("\n[bold yellow]Related Snippets:[/bold yellow]")
            related_snippets = get_related_snippets(snippet_id, top_k=5, same_language=True)

            if related_snippets:
                for i, rel in enumerate(related_snippets, 1):
                    # Create concise display
                    lang_badge = f"[blue]{rel['language']}[/blue]"
                    tags_str = f"[magenta]{', '.join(rel.get('tags', [])[:3])}[/magenta]" if rel.get('tags') else ""

                    display_parts = [f"  {i}. [cyan]#{rel['id']}[/cyan]", rel['title'][:60]]
                    if tags_str:
                        display_parts.append(tags_str)

                    console.print(" • ".join(display_parts))

                console.print(f"\n[dim]Tip: Use 'snipvault show <id>' to view any related snippet[/dim]")
            else:
                console.print("  [dim]No related snippets found[/dim]")

    except Exception as e:
        if "not found" not in str(e).lower():
            console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()