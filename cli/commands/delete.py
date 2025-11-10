"""Delete command for removing snippets."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from db.queries import get_snippet_by_id, delete_snippet
from db.setup import get_pinecone_index

console = Console()


@click.command()
@click.argument('snippet_id', type=int)
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt')
def delete(snippet_id, force):
    """
    Delete a snippet from SnipVault.

    Examples:
        snipvault delete 5
        snipvault delete 10 --force
    """
    try:
        # Step 1: Fetch snippet to confirm it exists
        console.print(f"\n[bold cyan]Looking up snippet ID {snippet_id}...[/bold cyan]")
        snippet = get_snippet_by_id(snippet_id)

        if not snippet:
            console.print(f"[red]✗ Snippet with ID {snippet_id} not found[/red]")
            raise click.Abort()

        # Display snippet details
        console.print(f"\n[yellow]Title:[/yellow] {snippet['title']}")
        console.print(f"[yellow]Language:[/yellow] {snippet['language']}")
        if snippet['tags']:
            console.print(f"[yellow]Tags:[/yellow] {', '.join(snippet['tags'])}")

        # Show code preview
        code_preview = snippet['code'][:200] + "..." if len(snippet['code']) > 200 else snippet['code']
        syntax = Syntax(code_preview, snippet['language'], theme="monokai", line_numbers=False)
        console.print("\n[yellow]Code:[/yellow]")
        console.print(syntax)

        # Confirmation prompt
        if not force:
            console.print("\n[bold red]⚠ This action cannot be undone![/bold red]")
            if not click.confirm(f"Are you sure you want to delete snippet {snippet_id}?"):
                console.print("[yellow]Deletion cancelled[/yellow]")
                return

        # Step 2: Delete from PostgreSQL
        console.print("\n[dim]→ Removing from database...[/dim]")
        success = delete_snippet(snippet_id)

        if not success:
            console.print("[red]✗ Failed to delete snippet from database[/red]")
            raise click.Abort()

        console.print("[green]✓ Removed from PostgreSQL[/green]")

        # Step 3: Delete from Pinecone
        console.print("[dim]→ Removing from Pinecone...[/dim]")
        try:
            index = get_pinecone_index()
            index.delete(ids=[str(snippet_id)])
            console.print("[green]✓ Removed from Pinecone[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ Warning: Failed to remove from Pinecone: {e}[/yellow]")
            console.print("[dim]The snippet was removed from PostgreSQL but may still exist in Pinecone[/dim]")

        # Success message
        console.print(Panel(
            f"[bold green]✓ Snippet {snippet_id} deleted successfully![/bold green]",
            title="Success",
            border_style="green"
        ))

    except Exception as e:
        if "not found" not in str(e).lower():
            console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()