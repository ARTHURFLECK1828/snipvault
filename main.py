#!/usr/bin/env python3
"""
SnipVault - LLM-Powered Code Snippet Manager

A terminal-first tool to store, tag, search, and manage code snippets
using PostgreSQL backend and Pinecone vector search with Gemini LLM.
"""

import click
from cli.commands import add, search, list_snippets, delete, show, update, export, import_snippets, index
from db.setup import initialize_all


@click.group()
@click.version_option(version='1.0.0', prog_name='SnipVault')
def cli():
    """
    SnipVault - LLM-Powered Code Snippet Manager

    Store and search code snippets using natural language with vector search.
    """
    pass


@cli.command()
def init():
    """Initialize SnipVault databases (PostgreSQL + Pinecone)."""
    click.echo("Initializing SnipVault...")
    success = initialize_all()

    if success:
        click.echo("\n✓ SnipVault is ready to use!")
        click.echo("\nNext steps:")
        click.echo("  1. Run migrations: snipvault migrate")
        click.echo("  2. Add your first snippet: snipvault add")
        click.echo("  3. Search snippets: snipvault search <query>")
        click.echo("  4. List all snippets: snipvault list")
    else:
        click.echo("\n✗ Initialization failed. Please check your .env configuration.")
        raise click.Abort()


@cli.command()
def migrate():
    """Run database migrations to add new features."""
    from db.migrate import run_all_migrations

    click.echo("Running database migrations...")
    click.echo()

    applied = run_all_migrations()

    if applied > 0:
        click.echo("\n✓ Migrations completed successfully!")
        click.echo("\nNew features enabled:")
        click.echo("  • Hybrid search (vector + keyword)")
        click.echo("  • Full-text search capabilities")
        click.echo("  • AI-generated summaries (column added)")
        click.echo("  • Usage tracking for future features")
    else:
        click.echo("\nℹ No new migrations to apply")


# Register commands
cli.add_command(add.add)
cli.add_command(search.search)
cli.add_command(list_snippets.list_snippets, name='list')
cli.add_command(delete.delete)
cli.add_command(show.show)
cli.add_command(update.update)
cli.add_command(export.export)
cli.add_command(import_snippets.import_snippets, name='import')
cli.add_command(index.index)

# GitHub integration commands
from cli.commands import github_import, github_gist
cli.add_command(github_import.github_import, name='github-import')
cli.add_command(github_gist.gist)

# Analytics and backup commands
from cli.commands import stats, backup
cli.add_command(stats.stats)
cli.add_command(backup.backup)


if __name__ == '__main__':
    cli()
