"""GitHub repository import command."""

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from pathlib import Path
from integrations.github import get_github_client
from utils.file_detector import detect_language, is_code_file
from utils.code_parser import generate_auto_tags
from db.queries import insert_snippet
from llm.embeddings import generate_embedding
from db.setup import get_pinecone_index
from utils.logger import get_logger

console = Console()
logger = get_logger(__name__)


@click.command()
@click.argument('repo_url')
@click.option('--path', '-p', default='', help='Specific path in repo to import')
@click.option('--branch', '-b', default='main', help='Branch to import from (default: main)')
@click.option('--recursive/--no-recursive', default=True, help='Recursively import subdirectories')
@click.option('--max-files', '-m', default=100, help='Maximum files to import (default: 100)')
@click.option('--auto-tag/--no-auto-tag', default=True, help='Auto-generate tags from code')
@click.option('--dry-run', is_flag=True, help='Preview without importing')
def github_import(repo_url, path, branch, recursive, max_files, auto_tag, dry_run):
    """
    Import code files from a GitHub repository.

    Examples:
        snipvault github-import https://github.com/user/repo
        snipvault github-import user/repo --path src/utils
        snipvault github-import user/repo --branch develop --max-files 50
    """
    try:
        console.print(f"\n[bold cyan]Importing from GitHub repository...[/bold cyan]\n")

        # Parse repo URL
        repo_name = _parse_repo_url(repo_url)
        console.print(f"Repository: [bold]{repo_name}[/bold]")
        console.print(f"Branch: [yellow]{branch}[/yellow]")
        console.print(f"Path: [yellow]{path or '(root)'}[/yellow]\n")

        # Get GitHub client
        github = get_github_client()
        repo = github.get_repo(repo_name)

        # Get files
        console.print("[dim]Scanning repository...[/dim]")
        files = _get_repo_files(repo, path, branch, recursive, max_files)

        if not files:
            console.print("[yellow]No code files found in repository.[/yellow]")
            return

        console.print(f"[green]Found {len(files)} code file(s)[/green]\n")

        if dry_run:
            console.print("[yellow]DRY RUN - Files that would be imported:[/yellow]\n")
            for file_path, language in files[:20]:
                console.print(f"  • {file_path} [{language}]")
            if len(files) > 20:
                console.print(f"  ... and {len(files) - 20} more")
            return

        # Import files
        index = get_pinecone_index()
        imported_count = 0
        skipped_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("Importing files...", total=len(files))

            for file_path, language in files:
                try:
                    # Get file content
                    file_content = repo.get_contents(file_path, ref=branch)

                    if file_content.size > 100000:  # Skip files > 100KB
                        logger.warning(f"Skipping large file: {file_path}")
                        skipped_count += 1
                        progress.advance(task)
                        continue

                    code = file_content.decoded_content.decode('utf-8')

                    # Generate title from path
                    title = f"{repo.name}/{file_path}"

                    # Generate tags
                    tags = [language, 'github', repo.owner.login]
                    if auto_tag:
                        auto_tags = generate_auto_tags(code, language, file_path)
                        tags.extend(auto_tags[:3])  # Limit auto tags

                    # Insert snippet
                    snippet_id = insert_snippet(
                        title=title,
                        code=code,
                        language=language,
                        tags=list(set(tags))  # Remove duplicates
                    )

                    # Generate and store embedding
                    snippet_text = f"{title}\n{code}"
                    embedding = generate_embedding(snippet_text)

                    if embedding:
                        index.upsert(vectors=[{
                            'id': str(snippet_id),
                            'values': embedding,
                            'metadata': {'language': language, 'tags': tags}
                        }])

                    imported_count += 1

                except Exception as e:
                    logger.error(f"Error importing {file_path}: {e}")
                    skipped_count += 1

                progress.advance(task)

        console.print(f"\n[bold green]✓ Import complete![/bold green]")
        console.print(f"  Imported: {imported_count}")
        console.print(f"  Skipped: {skipped_count}\n")

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        logger.error(f"GitHub import failed: {e}")
        raise click.Abort()


def _parse_repo_url(repo_url: str) -> str:
    """
    Parse GitHub repo URL to get owner/repo format.

    Args:
        repo_url: GitHub URL or owner/repo

    Returns:
        owner/repo string
    """
    # Already in owner/repo format
    if '/' in repo_url and 'github.com' not in repo_url:
        return repo_url

    # Parse from URL
    if 'github.com' in repo_url:
        parts = repo_url.rstrip('/').split('/')
        return f"{parts[-2]}/{parts[-1].replace('.git', '')}"

    raise ValueError(f"Invalid GitHub repo URL: {repo_url}")


def _get_repo_files(repo, path: str, branch: str, recursive: bool, max_files: int) -> list:
    """
    Get list of code files from repository.

    Args:
        repo: GitHub repo object
        path: Path within repo
        branch: Branch name
        recursive: Scan recursively
        max_files: Maximum files to return

    Returns:
        List of (file_path, language) tuples
    """
    files = []

    def scan_directory(dir_path: str):
        if len(files) >= max_files:
            return

        try:
            contents = repo.get_contents(dir_path, ref=branch)

            if not isinstance(contents, list):
                contents = [contents]

            for content in contents:
                if len(files) >= max_files:
                    break

                if content.type == "file":
                    file_path = content.path

                    # Check if it's a code file
                    if is_code_file(file_path):
                        language = detect_language(file_path)
                        files.append((file_path, language))

                elif content.type == "dir" and recursive:
                    # Ignore common directories
                    dir_name = content.name.lower()
                    if dir_name not in ['node_modules', '.git', 'dist', 'build', '__pycache__', 'vendor']:
                        scan_directory(content.path)

        except Exception as e:
            logger.warning(f"Error scanning {dir_path}: {e}")

    scan_directory(path)
    return files
