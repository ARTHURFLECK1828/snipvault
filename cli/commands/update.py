"""Update command for editing existing snippets."""

import click
import os
import tempfile
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from db.queries import get_snippet_by_id, update_snippet
from db.setup import get_pinecone_index
from llm.embeddings import generate_embedding, prepare_snippet_text

console = Console()


@click.command()
@click.argument('snippet_id', type=int)
@click.option('--title', help='New title')
@click.option('--code', help='New code')
@click.option('--lang', '--language', help='New programming language')
@click.option('--tags', '-t', multiple=True, help='New tags (replaces existing tags)')
@click.option('--editor', '-e', is_flag=True, help='Edit code in $EDITOR')
def update(snippet_id, title, code, lang, tags, editor):
    """
    Update an existing snippet and regenerate embeddings.

    Examples:
        snipvault update 5 --title "New Title"
        snipvault update 10 --lang python
        snipvault update 15 --editor
        snipvault update 20 --tags algorithm,sorting
    """
    try:
        # Fetch existing snippet
        console.print(f"\n[bold cyan]Fetching snippet ID {snippet_id}...[/bold cyan]")
        snippet = get_snippet_by_id(snippet_id)

        if not snippet:
            console.print(f"[red]✗ Snippet with ID {snippet_id} not found[/red]")
            raise click.Abort()

        # Show current snippet
        console.print(f"\n[yellow]Current Title:[/yellow] {snippet['title']}")
        console.print(f"[yellow]Current Language:[/yellow] {snippet['language']}")
        if snippet['tags']:
            console.print(f"[yellow]Current Tags:[/yellow] {', '.join(snippet['tags'])}")

        # Handle editor mode
        if editor:
            console.print("\n[dim]Opening code in $EDITOR...[/dim]")
            editor_cmd = os.environ.get('EDITOR', 'nano')

            # Create temporary file with current code
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=f'.{snippet["language"]}',
                delete=False
            ) as tf:
                tf.write(snippet['code'])
                temp_file = tf.name

            try:
                # Open in editor
                subprocess.run([editor_cmd, temp_file], check=True)

                # Read edited content
                with open(temp_file, 'r') as f:
                    code = f.read()

                os.unlink(temp_file)
            except Exception as e:
                console.print(f"[red]✗ Editor error: {e}[/red]")
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                raise click.Abort()

        # Parse tags if provided
        tags_list = None
        if tags:
            tags_list = []
            for tag_group in tags:
                tags_list.extend([t.strip() for t in tag_group.split(',') if t.strip()])
            # Remove duplicates
            seen = set()
            tags_list = [t for t in tags_list if not (t in seen or seen.add(t))]

        # Check if anything changed
        has_changes = False
        code_changed = False

        if title and title != snippet['title']:
            has_changes = True
        if code and code != snippet['code']:
            has_changes = True
            code_changed = True
        if lang and lang != snippet['language']:
            has_changes = True
        if tags_list is not None and tags_list != snippet['tags']:
            has_changes = True

        if not has_changes:
            console.print("\n[yellow]No changes detected[/yellow]")
            return

        # Show what will be updated
        console.print("\n[bold cyan]Updating snippet...[/bold cyan]")
        if title:
            console.print(f"[yellow]New Title:[/yellow] {title}")
        if code:
            syntax = Syntax(
                code[:200] + "..." if len(code) > 200 else code,
                lang or snippet['language'],
                theme="monokai",
                line_numbers=False
            )
            console.print("\n[yellow]New Code:[/yellow]")
            console.print(syntax)
        if lang:
            console.print(f"[yellow]New Language:[/yellow] {lang}")
        if tags_list is not None:
            console.print(f"[yellow]New Tags:[/yellow] {', '.join(tags_list)}")

        # Step 1: Update PostgreSQL
        console.print("\n[dim]→ Updating database...[/dim]")
        success = update_snippet(
            snippet_id,
            title=title,
            code=code,
            language=lang,
            tags=tags_list
        )

        if not success:
            console.print("[red]✗ Failed to update snippet in database[/red]")
            raise click.Abort()

        console.print("[green]✓ Updated in PostgreSQL[/green]")

        # Step 2: Regenerate embedding if code changed
        if code_changed:
            console.print("[dim]→ Regenerating embedding with Gemini...[/dim]")

            # Use new values or fall back to existing
            final_title = title or snippet['title']
            final_code = code
            final_tags = tags_list if tags_list is not None else snippet['tags']

            snippet_text = prepare_snippet_text(final_title, final_code, final_tags)
            embedding = generate_embedding(snippet_text)

            if not embedding:
                console.print("[yellow]⚠ Failed to generate new embedding[/yellow]")
            else:
                console.print("[green]✓ Generated new embedding[/green]")

                # Step 3: Update Pinecone
                console.print("[dim]→ Updating vector in Pinecone...[/dim]")
                try:
                    index = get_pinecone_index()
                    index.upsert(
                        vectors=[
                            {
                                "id": str(snippet_id),
                                "values": embedding,
                                "metadata": {
                                    "title": final_title,
                                    "language": lang or snippet['language'],
                                    "tags": final_tags
                                }
                            }
                        ]
                    )
                    console.print("[green]✓ Updated in Pinecone[/green]")
                except Exception as e:
                    console.print(f"[yellow]⚠ Warning: Failed to update Pinecone: {e}[/yellow]")

        # Success message
        console.print(Panel(
            f"[bold green]✓ Snippet {snippet_id} updated successfully![/bold green]",
            title="Success",
            border_style="green"
        ))

    except Exception as e:
        if "not found" not in str(e).lower():
            console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()