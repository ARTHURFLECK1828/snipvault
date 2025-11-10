"""Backup and restore commands for SnipVault."""

import click
import json
import subprocess
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from db.queries import list_all_snippets, insert_snippet
from db.setup import get_pinecone_index, get_db_connection
from llm.embeddings import generate_embedding
from utils.logger import get_logger
from config import get_config

console = Console()
logger = get_logger(__name__)


@click.group()
def backup():
    """Backup and restore commands."""
    pass


@backup.command('create')
@click.option('--output', '-o', help='Output directory (default: ~/.snipvault/backups)')
@click.option('--include-vectors/--no-vectors', default=True, help='Include vector embeddings')
def backup_create(output, include_vectors):
    """
    Create a backup of all snippets and data.

    Examples:
        snipvault backup create
        snipvault backup create --output ./backups
        snipvault backup create --no-vectors
    """
    try:
        # Determine output directory
        if output:
            backup_dir = Path(output)
        else:
            backup_dir = Path.home() / '.snipvault' / 'backups'

        backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"snipvault_backup_{timestamp}"
        backup_path = backup_dir / f"{backup_name}.json"

        console.print(f"\n[bold cyan]Creating backup...[/bold cyan]")
        console.print(f"Output: {backup_path}\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching snippets...", total=None)

            # Get all snippets
            snippets = list_all_snippets(limit=100000)
            progress.update(task, description=f"Found {len(snippets)} snippets")

            # Prepare backup data
            backup_data = {
                'version': '1.0.0',
                'timestamp': datetime.now().isoformat(),
                'total_snippets': len(snippets),
                'include_vectors': include_vectors,
                'snippets': []
            }

            # Get vector embeddings if requested
            if include_vectors:
                progress.update(task, description="Fetching vector embeddings...")
                index = get_pinecone_index()

                snippet_ids = [str(s['id']) for s in snippets]
                vectors = index.fetch(ids=snippet_ids)

                # Map embeddings to snippets
                embeddings_map = {
                    v_id: data['values']
                    for v_id, data in vectors.get('vectors', {}).items()
                }
            else:
                embeddings_map = {}

            # Build backup
            progress.update(task, description="Building backup...")

            for snippet in snippets:
                snippet_data = {
                    'id': snippet['id'],
                    'title': snippet['title'],
                    'code': snippet['code'],
                    'language': snippet['language'],
                    'tags': snippet['tags'],
                    'created_at': snippet['created_at'].isoformat() if hasattr(snippet['created_at'], 'isoformat') else str(snippet['created_at']),
                    'summary': snippet.get('summary')
                }

                # Add embedding if available
                if include_vectors and str(snippet['id']) in embeddings_map:
                    snippet_data['embedding'] = embeddings_map[str(snippet['id'])]

                backup_data['snippets'].append(snippet_data)

            # Write backup
            progress.update(task, description="Writing backup file...")

            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2)

        # Create PostgreSQL dump
        console.print("\n[dim]Creating PostgreSQL dump...[/dim]")
        pg_dump_path = backup_dir / f"{backup_name}.sql"

        try:
            config = get_config()
            subprocess.run([
                'pg_dump',
                '-h', config.get('database.postgres.host', 'localhost'),
                '-U', config.get('database.postgres.user', 'postgres'),
                '-d', config.get('database.postgres.database', 'snipvault'),
                '-f', str(pg_dump_path)
            ], check=True)

            console.print(f"[green]✓ PostgreSQL dump created: {pg_dump_path.name}[/green]")

        except Exception as e:
            logger.warning(f"PostgreSQL dump failed: {e}")
            console.print(f"[yellow]⚠ PostgreSQL dump failed (continuing...)[/yellow]")

        console.print(f"\n[bold green]✓ Backup created successfully![/bold green]")
        console.print(f"Location: {backup_path}")
        console.print(f"Size: {backup_path.stat().st_size / 1024:.1f} KB\n")

    except Exception as e:
        console.print(f"\n[red]✗ Backup failed: {e}[/red]")
        logger.error(f"Backup failed: {e}")
        raise click.Abort()


@backup.command('restore')
@click.argument('backup_file')
@click.option('--clear-existing/--keep-existing', default=False, help='Clear existing data before restore')
@click.option('--dry-run', is_flag=True, help='Preview without restoring')
def backup_restore(backup_file, clear_existing, dry_run):
    """
    Restore from a backup file.

    Examples:
        snipvault backup restore backup.json
        snipvault backup restore backup.json --clear-existing
        snipvault backup restore backup.json --dry-run
    """
    try:
        backup_path = Path(backup_file)

        if not backup_path.exists():
            console.print(f"[red]✗ Backup file not found: {backup_file}[/red]")
            raise click.Abort()

        console.print(f"\n[bold cyan]Restoring from backup...[/bold cyan]")
        console.print(f"File: {backup_path}\n")

        # Load backup
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)

        console.print(f"Backup version: {backup_data.get('version', 'unknown')}")
        console.print(f"Timestamp: {backup_data.get('timestamp', 'unknown')}")
        console.print(f"Snippets: {backup_data.get('total_snippets', 0)}")
        console.print(f"Includes vectors: {backup_data.get('include_vectors', False)}\n")

        if dry_run:
            console.print("[yellow]DRY RUN - No changes will be made[/yellow]\n")
            return

        # Confirm if clearing existing data
        if clear_existing:
            if not click.confirm("⚠ This will DELETE all existing snippets. Continue?"):
                console.print("\n[yellow]Restore cancelled[/yellow]")
                return

            console.print("\n[dim]Clearing existing data...[/dim]")
            # Clear PostgreSQL and Pinecone (implementation depends on your setup)

        # Restore snippets
        index = get_pinecone_index()
        restored_count = 0
        skipped_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Restoring snippets...", total=len(backup_data['snippets']))

            for snippet_data in backup_data['snippets']:
                try:
                    # Insert snippet
                    snippet_id = insert_snippet(
                        title=snippet_data['title'],
                        code=snippet_data['code'],
                        language=snippet_data['language'],
                        tags=snippet_data['tags'],
                        summary=snippet_data.get('summary')
                    )

                    # Restore embedding
                    if 'embedding' in snippet_data:
                        embedding = snippet_data['embedding']
                    else:
                        # Generate new embedding
                        snippet_text = f"{snippet_data['title']}\n{snippet_data['code']}"
                        embedding = generate_embedding(snippet_text)

                    if embedding:
                        index.upsert(vectors=[{
                            'id': str(snippet_id),
                            'values': embedding,
                            'metadata': {
                                'language': snippet_data['language'],
                                'tags': snippet_data['tags']
                            }
                        }])

                    restored_count += 1

                except Exception as e:
                    logger.error(f"Error restoring snippet: {e}")
                    skipped_count += 1

                progress.advance(task)

        console.print(f"\n[bold green]✓ Restore complete![/bold green]")
        console.print(f"Restored: {restored_count}")
        console.print(f"Skipped: {skipped_count}\n")

    except Exception as e:
        console.print(f"\n[red]✗ Restore failed: {e}[/red]")
        logger.error(f"Restore failed: {e}")
        raise click.Abort()


@backup.command('list')
@click.option('--directory', '-d', help='Backup directory (default: ~/.snipvault/backups)')
def backup_list(directory):
    """List available backups."""
    try:
        if directory:
            backup_dir = Path(directory)
        else:
            backup_dir = Path.home() / '.snipvault' / 'backups'

        if not backup_dir.exists():
            console.print("[yellow]No backups found[/yellow]")
            return

        backups = sorted(backup_dir.glob('snipvault_backup_*.json'), reverse=True)

        if not backups:
            console.print("[yellow]No backups found[/yellow]")
            return

        console.print(f"\n[bold cyan]Available Backups ({backup_dir})[/bold cyan]\n")

        from rich.table import Table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("File", style="bold")
        table.add_column("Size", style="yellow")
        table.add_column("Created", style="dim")

        for backup_file in backups:
            size_kb = backup_file.stat().st_size / 1024
            created = datetime.fromtimestamp(backup_file.stat().st_mtime)

            table.add_row(
                backup_file.name,
                f"{size_kb:.1f} KB",
                created.strftime('%Y-%m-%d %H:%M')
            )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise click.Abort()
