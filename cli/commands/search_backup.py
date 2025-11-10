"""Search command for finding snippets using natural language."""

import click
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel
from db.queries import get_snippets_by_ids
from db.setup import get_pinecone_index
from llm.embeddings import generate_query_embedding
from llm.query_enhancer import enhance_query

console = Console()


@click.command()
@click.argument('query')
@click.option('--top', '-k', default=5, help='Number of results to return (default: 5)')
@click.option('--no-enhance', is_flag=True, help='Disable query enhancement')
@click.option('--lang', '--language', help='Filter by programming language')
@click.option('--tags', help='Filter by tags (comma-separated)')
@click.option('--since', help='Filter by date (YYYY-MM-DD)')
def search(query, top, no_enhance, lang, tags, since):
    """
    Search for code snippets using natural language.

    Examples:
        snipvault search "API for payment processing"
        snipvault search "algorithm for sorting" --top 3
        snipvault search "react hooks" --lang javascript
        snipvault search "authentication" --tags api,security
        snipvault search "database query" --since 2024-01-01
    """
    try:
        console.print(f"\n[bold cyan]Searching for:[/bold cyan] {query}\n")

        # Step 1: Enhance query using LLM (unless disabled)
        if not no_enhance:
            console.print("[dim]→ Enhancing query with Gemini...[/dim]")
            enhanced_query = enhance_query(query)
            if enhanced_query != query:
                console.print(f"[dim]  Enhanced: {enhanced_query}[/dim]\n")
        else:
            enhanced_query = query

        # Step 2: Generate query embedding
        console.print("[dim]→ Generating query embedding...[/dim]")
        query_embedding = generate_query_embedding(enhanced_query)

        if not query_embedding:
            console.print("[red]✗ Failed to generate query embedding[/red]")
            raise click.Abort()

        # Step 3: Build metadata filters
        metadata_filter = {}
        if lang:
            metadata_filter['language'] = {"$eq": lang}
            console.print(f"[dim]  Filter: language = {lang}[/dim]")

        if tags:
            # Parse comma-separated tags
            tag_list = [t.strip() for t in tags.split(',')]
            # Pinecone requires tags to be in the metadata
            # We'll use $in operator to match any of the provided tags
            if len(tag_list) == 1:
                metadata_filter['tags'] = {"$in": tag_list}
            else:
                metadata_filter['tags'] = {"$in": tag_list}
            console.print(f"[dim]  Filter: tags in {tag_list}[/dim]")

        # Step 3: Search in Pinecone
        console.print("[dim]→ Searching vector database...[/dim]\n")
        index = get_pinecone_index()

        query_params = {
            'vector': query_embedding,
            'top_k': top,
            'include_metadata': True
        }

        if metadata_filter:
            query_params['filter'] = metadata_filter

        results = index.query(**query_params)

        # Check if any results found
        if not results['matches']:
            console.print("[yellow]No snippets found matching your query.[/yellow]")
            console.print("\nTry:")
            console.print("  • Using different keywords")
            console.print("  • Adding more snippets with: snipvault add")
            return

        # Step 4: Fetch full snippet details from PostgreSQL
        snippet_ids = [match['id'] for match in results['matches']]
        snippets = get_snippets_by_ids(snippet_ids)

        # Apply date filter if specified
        if since:
            from datetime import datetime
            try:
                since_date = datetime.strptime(since, '%Y-%m-%d')
                snippets = [s for s in snippets if s['created_at'] >= since_date]
                if not snippets:
                    console.print(f"[yellow]No snippets found since {since}[/yellow]")
                    return
            except ValueError:
                console.print(f"[red]✗ Invalid date format. Use YYYY-MM-DD (e.g., 2024-01-01)[/red]")
                raise click.Abort()

        # Create a mapping for easy lookup
        snippets_dict = {str(s['id']): s for s in snippets}

        # Step 5: Display results
        console.print(f"[bold green]Found {len(snippets)} results:[/bold green]\n")

        result_count = 0
        for match in results['matches']:
            snippet_id = match['id']
            score = match['score']
            snippet = snippets_dict.get(snippet_id)

            if not snippet:
                continue

            result_count += 1

            # Create title with metadata
            title_parts = [f"[bold]{snippet['title']}[/bold]"]
            title_parts.append(f"[dim](ID: {snippet['id']})[/dim]")
            title_parts.append(f"[blue]{snippet['language']}[/blue]")

            if snippet.get('tags'):
                tags_str = ", ".join(snippet['tags'])
                title_parts.append(f"[magenta]{tags_str}[/magenta]")

            # Similarity score
            score_color = "green" if score > 0.8 else "yellow" if score > 0.6 else "red"
            title_parts.append(f"[{score_color}]similarity: {score:.2%}[/{score_color}]")

            title_line = " • ".join(title_parts)

            # Code preview (first 300 chars)
            code = snippet['code']
            if len(code) > 300:
                code_preview = code[:300] + "..."
            else:
                code_preview = code

            # Display with syntax highlighting
            syntax = Syntax(
                code_preview,
                snippet['language'],
                theme="monokai",
                line_numbers=False,
                word_wrap=True
            )

            panel = Panel(
                syntax,
                title=f"[{result_count}] {title_line}",
                border_style=score_color,
                expand=False
            )

            console.print(panel)
            console.print()

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()
