"""Enhanced search command with hybrid search and intelligent ranking."""

import click
from datetime import datetime
from rich.console import Console, Group
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from search.hybrid import hybrid_search
from search.ranking import rerank_results, get_score_explanation
from search.fuzzy import fuzzy_search

console = Console()


@click.command()
@click.argument('query')
@click.option('--top', '-k', default=5, help='Number of results to return (default: 5)')
@click.option('--page', '-p', default=1, help='Page number for pagination (default: 1)')
@click.option('--no-enhance', is_flag=True, help='Disable query enhancement')
@click.option('--lang', '--language', help='Filter by programming language')
@click.option('--tags', help='Filter by tags (comma-separated)')
@click.option('--since', help='Filter by date (YYYY-MM-DD)')
@click.option('--hybrid/--vector-only', default=True, help='Use hybrid search (default: hybrid)')
@click.option('--fuzzy/--no-fuzzy', default=True, help='Enable typo tolerance (default: enabled)')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed scoring breakdown')
def search(query, top, page, no_enhance, lang, tags, since, hybrid, fuzzy, verbose):
    """
    Search for code snippets using natural language with hybrid search.

    Examples:
        snipvault search "API for payment processing"
        snipvault search "algorithm for sorting" --top 3
        snipvault search "react hooks" --lang javascript
        snipvault search "authentication" --tags api,security
        snipvault search "database query" --since 2024-01-01
        snipvault search "authenitcation" --fuzzy  # Auto-corrects typos
        snipvault search "API" --verbose  # Show score breakdown
    """
    try:
        console.print(f"\n[bold cyan]Searching for:[/bold cyan] {query}\n")

        # Parse tags
        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(',')]

        # Perform search (with or without fuzzy matching)
        if fuzzy:
            search_result = fuzzy_search(
                query,
                search_func=lambda q, **kwargs: hybrid_search(
                    q,
                    use_enhancement=not no_enhance,
                    language=lang,
                    tags=tag_list,
                    **kwargs
                ) if hybrid else vector_only_search(q, lang, tag_list, **kwargs),
                top_k=top * 2  # Get more for re-ranking
            )

            results = search_result['results']

            # Show suggestion if query was corrected
            if search_result.get('was_corrected'):
                console.print(f"[yellow]ℹ {search_result['suggestion']}[/yellow]\n")

        else:
            if hybrid:
                results = hybrid_search(
                    query,
                    use_enhancement=not no_enhance,
                    language=lang,
                    tags=tag_list,
                    top_k=top * 2
                )
            else:
                results = vector_only_search(query, lang, tag_list, top=top * 2)

        if not results:
            console.print("[yellow]No snippets found matching your query.[/yellow]")
            console.print("\nTry:")
            console.print("  • Using different keywords")
            console.print("  • Checking for typos")
            console.print("  • Adding more snippets with: snipvault add")
            return

        # Re-rank results with intelligent scoring
        console.print(f"[dim]→ Ranking {len(results)} results...[/dim]\n")
        ranked_results = rerank_results(results, query)

        # Apply date filter if specified
        if since:
            try:
                since_date = datetime.strptime(since, '%Y-%m-%d')
                ranked_results = [
                    r for r in ranked_results
                    if r['snippet']['created_at'] >= since_date
                ]
                if not ranked_results:
                    console.print(f"[yellow]No snippets found since {since}[/yellow]")
                    return
            except ValueError:
                console.print(f"[red]✗ Invalid date format. Use YYYY-MM-DD (e.g., 2024-01-01)[/red]")
                raise click.Abort()

        # Apply pagination
        from utils.pagination import Paginator, format_pagination_info, get_page_navigation

        paginator = Paginator(page_size=top)
        paginated = paginator.paginate(ranked_results, page=page)

        # Display results
        console.print(f"[bold green]Found {paginated.total_items} results:[/bold green]")
        console.print(f"[dim]{format_pagination_info(paginated)}[/dim]\n")

        final_results = paginated.items

        for i, result in enumerate(final_results, 1):
            snippet = result['snippet']

            # Create title with metadata
            title_parts = [f"[bold]{snippet['title']}[/bold]"]
            title_parts.append(f"[dim](ID: {snippet['id']})[/dim]")
            title_parts.append(f"[blue]{snippet['language']}[/blue]")

            if snippet.get('tags'):
                tags_str = ", ".join(snippet['tags'])
                title_parts.append(f"[magenta]{tags_str}[/magenta]")

            # Score display
            score = result.get('final_score', result.get('score', 0))
            score_color = "green" if score > 0.7 else "yellow" if score > 0.4 else "red"
            title_parts.append(f"[{score_color}]score: {score:.1%}[/{score_color}]")

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

            # Build panel content with renderables
            panel_content = []

            # Add summary if available
            if snippet.get('summary'):
                panel_content.append(Text(snippet['summary'], style="italic"))
                panel_content.append(Text(""))  # Empty line

            # Add code syntax
            panel_content.append(syntax)

            # Verbose mode: show score breakdown
            if verbose and 'score_breakdown' in result:
                explanation = get_score_explanation(result)
                panel_content.append(Text(""))  # Empty line
                panel_content.append(Text(explanation, style="dim"))

            panel = Panel(
                Group(*panel_content),
                title=f"[{i}] {title_line}",
                border_style=score_color,
                expand=False
            )

            console.print(panel)
            console.print()

        # Show pagination navigation
        nav = get_page_navigation(paginated)
        if nav:
            console.print(f"[dim]{nav}[/dim]\n")

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()


def vector_only_search(query, language, tags, top=10):
    """
    Fallback to vector-only search (old behavior).

    Args:
        query: Search query
        language: Language filter
        tags: Tags filter
        top: Number of results

    Returns:
        List of results
    """
    from llm.embeddings import generate_query_embedding
    from llm.query_enhancer import enhance_query
    from db.setup import get_pinecone_index
    from db.queries import get_snippets_by_ids

    enhanced_query = enhance_query(query)
    query_embedding = generate_query_embedding(enhanced_query)

    if not query_embedding:
        return []

    index = get_pinecone_index()

    # Build filters
    filters = {}
    if language:
        filters['language'] = {'$eq': language}
    if tags:
        filters['tags'] = {'$in': tags}

    query_params = {
        'vector': query_embedding,
        'top_k': top,
        'include_metadata': True
    }
    if filters:
        query_params['filter'] = filters

    vector_results = index.query(**query_params)

    # Get snippets
    snippet_ids = [match['id'] for match in vector_results['matches']]
    snippets = get_snippets_by_ids(snippet_ids)
    snippet_dict = {str(s['id']): s for s in snippets}

    # Format results
    results = []
    for match in vector_results['matches']:
        snippet = snippet_dict.get(match['id'])
        if snippet:
            results.append({
                'id': match['id'],
                'score': match['score'],
                'snippet': snippet
            })

    return results
