"""Index command for bulk importing code from directories."""

import click
import os
import hashlib
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from db.queries import insert_snippet, list_all_snippets
from db.setup import get_pinecone_index
from llm.embeddings import generate_embedding, prepare_snippet_text
from utils.file_detector import (
    detect_language,
    should_skip_file,
    should_skip_directory,
    is_text_file
)
from utils.code_parser import (
    extract_python_elements,
    generate_auto_tags,
    should_extract_as_snippet,
    extract_docstring_from_code
)
from utils.ignore_patterns import IgnorePatternMatcher, get_default_ignore_patterns

console = Console()


def compute_code_hash(code: str) -> str:
    """Compute hash of code for duplicate detection."""
    # Normalize whitespace for better duplicate detection
    normalized = ' '.join(code.split())
    return hashlib.md5(normalized.encode()).hexdigest()


def scan_directory(directory, recursive=True, lang_filter=None, ignore_matcher=None):
    """
    Scan directory for code files.

    Args:
        directory: Directory path to scan
        recursive: Whether to scan recursively
        lang_filter: Optional language filter
        ignore_matcher: IgnorePatternMatcher instance

    Returns:
        List of (file_path, language) tuples
    """
    files = []
    dir_path = Path(directory)

    if not dir_path.exists():
        return files

    if not dir_path.is_dir():
        # Single file
        if not should_skip_file(directory) and is_text_file(directory):
            lang = detect_language(directory)
            if not lang_filter or lang == lang_filter:
                files.append((str(directory), lang))
        return files

    # Scan directory
    for root, dirs, filenames in os.walk(directory):
        # Filter directories
        dirs[:] = [
            d for d in dirs
            if not should_skip_directory(d) and
            (not ignore_matcher or not ignore_matcher.should_ignore(os.path.join(root, d), is_dir=True))
        ]

        if not recursive:
            dirs.clear()

        for filename in filenames:
            file_path = os.path.join(root, filename)

            # Skip if matches ignore patterns
            if ignore_matcher and ignore_matcher.should_ignore(file_path, is_dir=False):
                continue

            # Skip binary files
            if should_skip_file(file_path):
                continue

            # Check if text file
            if not is_text_file(file_path):
                continue

            # Detect language
            lang = detect_language(file_path)

            # Apply language filter
            if lang_filter and lang != lang_filter:
                continue

            files.append((file_path, lang))

    return files


@click.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--recursive', '-r', is_flag=True, default=True, help='Scan directories recursively')
@click.option('--lang', '--language', help='Filter by programming language')
@click.option('--extract', '-e', is_flag=True, help='Extract functions/classes as separate snippets')
@click.option('--use-gitignore', is_flag=True, default=True, help='Respect .gitignore patterns')
@click.option('--exclude', multiple=True, help='Additional patterns to exclude')
@click.option('--dry-run', is_flag=True, help='Show what would be imported without importing')
@click.option('--auto-tag', is_flag=True, default=True, help='Automatically generate tags')
def index(path, recursive, lang, extract, use_gitignore, exclude, dry_run, auto_tag):
    """
    Index and import code files from a directory or codebase.

    Examples:
        snipvault index ~/projects/myapp
        snipvault index ~/repos --lang python --extract
        snipvault index ./src --exclude "*.test.js" --exclude "*.spec.js"
        snipvault index . --no-recursive --dry-run
    """
    try:
        console.print(f"\n[bold cyan]Scanning: {path}[/bold cyan]")

        # Setup ignore patterns
        ignore_patterns = get_default_ignore_patterns()

        if use_gitignore:
            ignore_matcher = IgnorePatternMatcher.from_directory(path)
            # Add default patterns
            for pattern in ignore_patterns:
                if pattern not in ignore_matcher.patterns:
                    ignore_matcher.patterns.append(pattern)
            ignore_matcher._compile_patterns()
        else:
            ignore_matcher = IgnorePatternMatcher(ignore_patterns)

        # Add custom exclude patterns
        for pattern in exclude:
            ignore_matcher.patterns.append(pattern)
        ignore_matcher._compile_patterns()

        # Scan for files
        console.print("[dim]→ Scanning for code files...[/dim]")
        files = scan_directory(path, recursive=recursive, lang_filter=lang, ignore_matcher=ignore_matcher)

        if not files:
            console.print("[yellow]No code files found[/yellow]")
            return

        console.print(f"[green]Found {len(files)} code file(s)[/green]\n")

        # Load existing snippets for duplicate detection
        console.print("[dim]→ Loading existing snippets for duplicate detection...[/dim]")
        existing_snippets = list_all_snippets(limit=10000)
        existing_hashes = {compute_code_hash(s['code']): s for s in existing_snippets}

        # Process files
        snippets_to_add = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Processing files...", total=len(files))

            for file_path, language in files:
                try:
                    # Read file
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()

                    # Check if too small or too large
                    if not should_extract_as_snippet(code, language):
                        progress.advance(task)
                        continue

                    relative_path = os.path.relpath(file_path, path)

                    # Extract elements if requested
                    if extract and language == 'python':
                        elements = extract_python_elements(code)

                        for element in elements:
                            element_code = element.get('code', '')
                            if not element_code or not should_extract_as_snippet(element_code, language):
                                continue

                            # Check for duplicates
                            code_hash = compute_code_hash(element_code)
                            if code_hash in existing_hashes:
                                continue

                            title = f"{element['name']} ({element['type']}) - {relative_path}"
                            tags = generate_auto_tags(element_code, language, relative_path) if auto_tag else [language]

                            # Add docstring to tags if available
                            if element.get('docstring'):
                                tags.append('documented')

                            snippets_to_add.append({
                                'title': title,
                                'code': element_code,
                                'language': language,
                                'tags': tags,
                                'source': file_path,
                                'hash': code_hash
                            })
                    else:
                        # Add whole file as snippet
                        code_hash = compute_code_hash(code)

                        # Check for duplicates
                        if code_hash in existing_hashes:
                            progress.advance(task)
                            continue

                        title = f"{os.path.basename(file_path)} - {relative_path}"
                        tags = generate_auto_tags(code, language, relative_path) if auto_tag else [language]

                        snippets_to_add.append({
                            'title': title,
                            'code': code,
                            'language': language,
                            'tags': tags,
                            'source': file_path,
                            'hash': code_hash
                        })

                    progress.advance(task)

                except Exception as e:
                    console.print(f"[yellow]⚠ Error processing {file_path}: {e}[/yellow]")
                    progress.advance(task)

        # Show summary
        console.print(f"\n[cyan]Found {len(snippets_to_add)} unique snippet(s) to import[/cyan]")
        duplicates_found = len(files) - len(snippets_to_add)
        if duplicates_found > 0:
            console.print(f"[dim]Skipped {duplicates_found} duplicate(s)[/dim]")

        if dry_run:
            console.print("\n[yellow]DRY RUN - No snippets will be imported[/yellow]\n")

            # Show sample of what would be imported
            table = Table(title="Sample Snippets (first 10)")
            table.add_column("Title", style="cyan")
            table.add_column("Language", style="green")
            table.add_column("Tags", style="magenta")

            for snippet in snippets_to_add[:10]:
                table.add_row(
                    snippet['title'][:60] + "..." if len(snippet['title']) > 60 else snippet['title'],
                    snippet['language'],
                    ', '.join(snippet['tags'][:5])
                )

            console.print(table)
            return

        if not snippets_to_add:
            console.print("[yellow]No new snippets to import[/yellow]")
            return

        # Confirm import
        if not click.confirm(f"\nImport {len(snippets_to_add)} snippet(s)?"):
            console.print("[yellow]Import cancelled[/yellow]")
            return

        # Import snippets
        success_count = 0
        error_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Importing snippets...", total=len(snippets_to_add))

            for snippet in snippets_to_add:
                try:
                    # Insert into PostgreSQL
                    snippet_id = insert_snippet(
                        snippet['title'],
                        snippet['code'],
                        snippet['language'],
                        snippet['tags']
                    )

                    if not snippet_id:
                        error_count += 1
                        progress.advance(task)
                        continue

                    # Generate embedding
                    snippet_text = prepare_snippet_text(
                        snippet['title'],
                        snippet['code'],
                        snippet['tags']
                    )
                    embedding = generate_embedding(snippet_text)

                    if not embedding:
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
                                    "title": snippet['title'],
                                    "language": snippet['language'],
                                    "tags": snippet['tags']
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

        # Final summary
        console.print(f"\n[bold green]✓ Import complete![/bold green]")
        console.print(f"  Success: {success_count}")
        if error_count > 0:
            console.print(f"  Errors: {error_count}")

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()
