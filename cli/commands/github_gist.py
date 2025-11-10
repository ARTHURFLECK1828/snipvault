"""GitHub Gist import/export commands."""

import click
from rich.console import Console
from rich.table import Table
from integrations.github import get_github_client
from db.queries import get_snippet_by_id, list_all_snippets, insert_snippet
from llm.embeddings import generate_embedding
from db.setup import get_pinecone_index
from utils.logger import get_logger
from config import get_config

console = Console()
logger = get_logger(__name__)


@click.group()
def gist():
    """Manage GitHub Gists."""
    pass


@gist.command('list')
@click.option('--limit', '-l', default=20, help='Number of gists to show')
def list_gists(limit):
    """List your GitHub Gists."""
    try:
        console.print("\n[bold cyan]Fetching your gists...[/bold cyan]\n")

        github = get_github_client()
        user = github.get_user()
        gists = list(user.get_gists()[:limit])

        if not gists:
            console.print("[yellow]No gists found.[/yellow]")
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim")
        table.add_column("Description", style="bold")
        table.add_column("Files", style="yellow")
        table.add_column("Public", style="green")
        table.add_column("Created", style="dim")

        for gist in gists:
            table.add_row(
                gist.id[:8] + "...",
                gist.description or "(no description)",
                str(len(gist.files)),
                "Yes" if gist.public else "No",
                gist.created_at.strftime('%Y-%m-%d')
            )

        console.print(table)
        console.print(f"\n[dim]Total: {len(gists)} gist(s)[/dim]\n")

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()


@gist.command('import')
@click.argument('gist_id', required=False)
@click.option('--all', 'import_all', is_flag=True, help='Import all your gists')
@click.option('--public-only', is_flag=True, help='Only import public gists')
def import_gist(gist_id, import_all, public_only):
    """
    Import gist(s) into SnipVault.

    Examples:
        snipvault gist import abc123def456
        snipvault gist import --all
        snipvault gist import --all --public-only
    """
    try:
        github = get_github_client()

        if import_all:
            console.print("\n[bold cyan]Importing all gists...[/bold cyan]\n")
            user = github.get_user()
            gists = user.get_gists()

            imported_count = 0
            for gist in gists:
                if public_only and not gist.public:
                    continue

                count = _import_single_gist(gist)
                imported_count += count

            console.print(f"\n[bold green]✓ Imported {imported_count} file(s) from gists[/bold green]\n")

        elif gist_id:
            console.print(f"\n[bold cyan]Importing gist {gist_id}...[/bold cyan]\n")
            gist = github.get_gist(gist_id)
            count = _import_single_gist(gist)
            console.print(f"\n[bold green]✓ Imported {count} file(s)[/bold green]\n")

        else:
            console.print("[red]✗ Please specify a gist ID or use --all[/red]")
            raise click.Abort()

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()


@gist.command('export')
@click.argument('snippet_id', type=int, required=False)
@click.option('--all', 'export_all', is_flag=True, help='Export all snippets as gists')
@click.option('--public/--private', default=False, help='Make gist public or private')
@click.option('--description', '-d', help='Gist description')
def export_gist(snippet_id, export_all, public, description):
    """
    Export snippet(s) to GitHub Gist.

    Examples:
        snipvault gist export 5 --public
        snipvault gist export 10 --description "Utility function"
    """
    try:
        github = get_github_client()
        config = get_config()

        # Get default visibility
        if public is None:
            public = config.get('github.default_visibility', 'private') == 'public'

        if export_all:
            console.print("\n[bold cyan]Exporting all snippets as gists...[/bold cyan]\n")
            snippets = list_all_snippets(limit=1000)

            exported_count = 0
            for snippet in snippets:
                gist_url = _export_single_snippet(github, snippet, public)
                if gist_url:
                    exported_count += 1

            console.print(f"\n[bold green]✓ Exported {exported_count} snippet(s)[/bold green]\n")

        elif snippet_id:
            snippet = get_snippet_by_id(snippet_id)

            if not snippet:
                console.print(f"[red]✗ Snippet {snippet_id} not found[/red]")
                raise click.Abort()

            console.print(f"\n[bold cyan]Exporting snippet {snippet_id}...[/bold cyan]\n")
            gist_url = _export_single_snippet(github, snippet, public, description)

            if gist_url:
                console.print(f"[bold green]✓ Gist created successfully![/bold green]")
                console.print(f"URL: [blue]{gist_url}[/blue]\n")

        else:
            console.print("[red]✗ Please specify a snippet ID or use --all[/red]")
            raise click.Abort()

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()


def _import_single_gist(gist) -> int:
    """
    Import files from a single gist.

    Args:
        gist: GitHub gist object

    Returns:
        Number of files imported
    """
    from utils.file_detector import detect_language

    index = get_pinecone_index()
    imported_count = 0

    for filename, file_obj in gist.files.items():
        try:
            language = detect_language(filename)
            code = file_obj.content

            title = f"Gist: {gist.description or filename}"
            tags = ['gist', 'github', language]

            # Insert snippet
            snippet_id = insert_snippet(
                title=title,
                code=code,
                language=language,
                tags=tags
            )

            # Generate embedding
            snippet_text = f"{title}\n{code}"
            embedding = generate_embedding(snippet_text)

            if embedding:
                index.upsert(vectors=[{
                    'id': str(snippet_id),
                    'values': embedding,
                    'metadata': {'language': language, 'tags': tags}
                }])

            console.print(f"  [green]✓[/green] {filename} ({language})")
            imported_count += 1

        except Exception as e:
            console.print(f"  [red]✗[/red] {filename}: {e}")
            logger.error(f"Error importing gist file {filename}: {e}")

    return imported_count


def _export_single_snippet(github, snippet: dict, public: bool, description: str = None) -> str:
    """
    Export a single snippet as a gist.

    Args:
        github: GitHub client
        snippet: Snippet dict
        public: Whether gist should be public
        description: Gist description

    Returns:
        Gist URL or None on error
    """
    try:
        # Generate filename
        ext_map = {
            'python': '.py', 'javascript': '.js', 'typescript': '.ts',
            'java': '.java', 'cpp': '.cpp', 'c': '.c', 'go': '.go',
            'rust': '.rs', 'ruby': '.rb', 'php': '.php', 'html': '.html',
            'css': '.css', 'sql': '.sql', 'bash': '.sh', 'json': '.json'
        }

        ext = ext_map.get(snippet['language'], '.txt')
        filename = snippet['title'].replace('/', '_').replace(' ', '_')[:50] + ext

        # Create gist
        gist_desc = description or snippet['title']
        files = {filename: {'content': snippet['code']}}

        gist = github.get_user().create_gist(
            public=public,
            files=files,
            description=gist_desc
        )

        return gist.html_url

    except Exception as e:
        console.print(f"  [red]✗[/red] {snippet['title']}: {e}")
        logger.error(f"Error exporting snippet {snippet['id']}: {e}")
        return None
