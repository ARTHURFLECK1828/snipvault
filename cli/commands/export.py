"""Export command for exporting snippets to files."""

import click
import json
from datetime import datetime
from pathlib import Path
from rich.console import Console
from db.queries import list_all_snippets, get_snippet_by_id

console = Console()


@click.command()
@click.option('--format', '-f', type=click.Choice(['json', 'markdown', 'md']), default='json', help='Export format')
@click.option('--output', '-o', help='Output file path (auto-generated if not specified)')
@click.option('--id', type=int, help='Export specific snippet by ID')
@click.option('--all', 'export_all', is_flag=True, help='Export all snippets')
def export(format, output, id, export_all):
    """
    Export snippets to JSON or Markdown format.

    Examples:
        snipvault export --all --format json
        snipvault export --id 5 --format markdown
        snipvault export --all -o my_snippets.json
    """
    try:
        # Determine what to export
        if id:
            snippets = [get_snippet_by_id(id)]
            if not snippets[0]:
                console.print(f"[red]✗ Snippet with ID {id} not found[/red]")
                raise click.Abort()
        elif export_all:
            console.print("[dim]→ Fetching all snippets...[/dim]")
            snippets = list_all_snippets(limit=10000)
        else:
            console.print("[yellow]Please specify --all or --id <ID>[/yellow]")
            console.print("Examples:")
            console.print("  snipvault export --all --format json")
            console.print("  snipvault export --id 5 --format markdown")
            raise click.Abort()

        if not snippets:
            console.print("[yellow]No snippets to export[/yellow]")
            return

        console.print(f"[cyan]Exporting {len(snippets)} snippet(s)...[/cyan]\n")

        # Normalize format
        if format == 'md':
            format = 'markdown'

        # Generate output filename if not specified
        if not output:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ext = 'json' if format == 'json' else 'md'
            output = f"snipvault_export_{timestamp}.{ext}"

        # Export based on format
        if format == 'json':
            export_json(snippets, output)
        else:
            export_markdown(snippets, output)

        console.print(f"[green]✓ Exported to: {output}[/green]")

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()


def export_json(snippets, output_file):
    """Export snippets to JSON format."""
    # Convert datetime objects to strings
    export_data = []
    for snippet in snippets:
        snippet_dict = dict(snippet)
        snippet_dict['created_at'] = snippet_dict['created_at'].isoformat() if snippet_dict.get('created_at') else None
        export_data.append(snippet_dict)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)


def export_markdown(snippets, output_file):
    """Export snippets to Markdown format."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# SnipVault Export\n\n")
        f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total snippets: {len(snippets)}\n\n")
        f.write("---\n\n")

        for snippet in snippets:
            f.write(f"## {snippet['title']}\n\n")
            f.write(f"**ID:** {snippet['id']}  \n")
            f.write(f"**Language:** {snippet['language']}  \n")

            if snippet.get('tags'):
                tags_str = ', '.join([f"`{tag}`" for tag in snippet['tags']])
                f.write(f"**Tags:** {tags_str}  \n")

            f.write(f"**Created:** {snippet['created_at']}  \n\n")

            # Code block
            f.write(f"```{snippet['language']}\n")
            f.write(snippet['code'])
            f.write("\n```\n\n")
            f.write("---\n\n")
