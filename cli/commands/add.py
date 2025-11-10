"""Add command for creating new snippets."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from db.queries import insert_snippet
from db.setup import get_pinecone_index
from llm.embeddings import generate_embedding, prepare_snippet_text

console = Console()


@click.command()
@click.argument('title', required=False)
@click.argument('code', required=False)
@click.option('--lang', '--language', default='plaintext', help='Programming language')
@click.option('--tags', '-t', multiple=True, help='Tags (comma-separated or multiple --tags flags)')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode for multi-line input')
def add(title, code, lang, tags, interactive):
    """
    Add a new code snippet to SnipVault.

    Examples:
        snipvault add "FizzBuzz" "for i in range(1,101): print('Fizz'*(i%3==0) or i)" --lang python --tags algorithm,loop
        snipvault add "API Call" "fetch('/api/data')" --lang javascript --tags api --tags fetch --tags async
        snipvault add --interactive
        snipvault add -i
    """
    try:
        # Interactive mode
        if interactive or (not title or not code):
            console.print("\n[bold cyan]Interactive Snippet Input[/bold cyan]")
            console.print("[dim]Press Ctrl+D (Unix) or Ctrl+Z (Windows) when done with code input[/dim]\n")

            # Get title
            if not title:
                title = click.prompt("Title")

            # Get language
            if lang == 'plaintext':
                lang = click.prompt("Language", default='plaintext')

            # Get tags
            if not tags:
                tags_input = click.prompt("Tags (comma-separated)", default='', show_default=False)
                if tags_input:
                    tags = (tags_input,)

            # Get multi-line code
            if not code:
                console.print("\n[yellow]Enter code (press Ctrl+D when done):[/yellow]")
                code_lines = []
                try:
                    while True:
                        line = input()
                        code_lines.append(line)
                except EOFError:
                    pass
                code = '\n'.join(code_lines)

                if not code.strip():
                    console.print("[red]✗ No code provided[/red]")
                    raise click.Abort()

            console.print()  # Add newline after input
        # Parse tags: support both comma-separated and multiple --tags flags
        tags_list = []
        if tags:
            for tag_group in tags:
                # Split by comma and strip whitespace
                tags_list.extend([t.strip() for t in tag_group.split(',') if t.strip()])

        # Remove duplicates while preserving order
        seen = set()
        tags_list = [t for t in tags_list if not (t in seen or seen.add(t))]

        # Show what's being added
        console.print("\n[bold cyan]Adding new snippet...[/bold cyan]")
        console.print(f"[yellow]Title:[/yellow] {title}")
        console.print(f"[yellow]Language:[/yellow] {lang}")
        if tags_list:
            console.print(f"[yellow]Tags:[/yellow] {', '.join(tags_list)}")

        # Display code with syntax highlighting
        syntax = Syntax(code, lang, theme="monokai", line_numbers=False)
        console.print("\n[yellow]Code:[/yellow]")
        console.print(syntax)

        # Step 1: Insert into PostgreSQL
        console.print("\n[dim]→ Saving to database...[/dim]")
        snippet_id = insert_snippet(title, code, lang, tags_list)

        if not snippet_id:
            console.print("[red]✗ Failed to save snippet to database[/red]")
            raise click.Abort()

        console.print(f"[green]✓ Saved to PostgreSQL (ID: {snippet_id})[/green]")

        # Step 2: Generate embedding
        console.print("[dim]→ Generating embedding with Gemini...[/dim]")
        snippet_text = prepare_snippet_text(title, code, tags_list)
        embedding = generate_embedding(snippet_text)

        if not embedding:
            console.print("[red]✗ Failed to generate embedding[/red]")
            raise click.Abort()

        console.print(f"[green]✓ Generated embedding (768 dimensions)[/green]")

        # Step 3: Store in Pinecone
        console.print("[dim]→ Storing vector in Pinecone...[/dim]")
        index = get_pinecone_index()

        index.upsert(
            vectors=[
                {
                    "id": str(snippet_id),
                    "values": embedding,
                    "metadata": {
                        "title": title,
                        "language": lang,
                        "tags": tags_list
                    }
                }
            ]
        )

        console.print("[green]✓ Stored in Pinecone[/green]")

        # Success message
        console.print(Panel(
            f"[bold green]✓ Snippet added successfully![/bold green]\n\n"
            f"ID: {snippet_id}\n"
            f"You can now search for it using natural language queries.",
            title="Success",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()
