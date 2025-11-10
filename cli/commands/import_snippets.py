"""Import command for importing snippets from files."""

import click
import json
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from db.queries import insert_snippet
from db.setup import get_pinecone_index
from llm.embeddings import generate_embedding, prepare_snippet_text

console = Console()


@click.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--format', '-f', type=click.Choice(['json', 'auto']), default='auto', help='Import format')
def import_snippets(file_path, format):
    """
    Import snippets from a JSON file.

    Examples:
        snipvault import snippets.json
        snipvault import backup.json --format json
    """
    try:
        file_path = Path(file_path)

        # Auto-detect format
        if format == 'auto':
            if file_path.suffix == '.json':
                format = 'json'
            else:
                console.print(f"[red]✗ Cannot auto-detect format for {file_path.suffix}[/red]")
                console.print("[yellow]Please specify --format json[/yellow]")
                raise click.Abort()

        # Read file
        console.print(f"[cyan]Reading from: {file_path}[/cyan]")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            console.print("[red]✗ Invalid format: expected a list of snippets[/red]")
            raise click.Abort()

        console.print(f"[cyan]Found {len(data)} snippet(s) to import[/cyan]\n")

        # Confirm import
        if not click.confirm(f"Import {len(data)} snippets?"):
            console.print("[yellow]Import cancelled[/yellow]")
            return

        # Import snippets with progress bar
        success_count = 0
        error_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Importing snippets...", total=len(data))

            for snippet_data in data:
                try:
                    # Extract fields
                    title = snippet_data.get('title')
                    code = snippet_data.get('code')
                    language = snippet_data.get('language', 'plaintext')
                    tags = snippet_data.get('tags', [])

                    if not title or not code:
                        console.print(f"[yellow]⚠ Skipping snippet: missing title or code[/yellow]")
                        error_count += 1
                        progress.advance(task)
                        continue

                    # Insert into PostgreSQL
                    snippet_id = insert_snippet(title, code, language, tags)

                    if not snippet_id:
                        console.print(f"[yellow]⚠ Failed to save: {title}[/yellow]")
                        error_count += 1
                        progress.advance(task)
                        continue

                    # Generate embedding
                    snippet_text = prepare_snippet_text(title, code, tags)
                    embedding = generate_embedding(snippet_text)

                    if not embedding:
                        console.print(f"[yellow]⚠ Failed to generate embedding for: {title}[/yellow]")
                        error_count += 1
                        progress.advance(task)
                        continue

                    # Store in Pinecone
                    index = get_pinecone_index()
                    index.upsert(
                        vectors=[
                            {
                                "id": str(snippet_id),
                                "values": embedding,
                                "metadata": {
                                    "title": title,
                                    "language": language,
                                    "tags": tags
                                }
                            }
                        ]
                    )

                    success_count += 1
                    progress.advance(task)

                except Exception as e:
                    console.print(f"[yellow]⚠ Error importing snippet: {e}[/yellow]")
                    error_count += 1
                    progress.advance(task)

        # Summary
        console.print(f"\n[bold green]✓ Import complete![/bold green]")
        console.print(f"  Success: {success_count}")
        if error_count > 0:
            console.print(f"  Errors: {error_count}")

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()
