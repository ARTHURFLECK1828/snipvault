"""Database migration runner for SnipVault."""

import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
from db.setup import get_db_connection


def ensure_migrations_table():
    """
    Create migrations tracking table if it doesn't exist.

    Returns:
        True if successful, False otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) UNIQUE NOT NULL,
                migration_hash VARCHAR(64) NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"✗ Failed to create migrations table: {e}")
        return False


def get_migration_hash(migration_file: Path) -> str:
    """
    Calculate SHA256 hash of migration file content.

    Args:
        migration_file: Path to migration file

    Returns:
        Hex digest of file hash
    """
    with open(migration_file, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def get_applied_migrations() -> List[Tuple[str, str]]:
    """
    Get list of already applied migrations.

    Returns:
        List of (migration_name, migration_hash) tuples
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT migration_name, migration_hash
            FROM schema_migrations
            ORDER BY applied_at
        """)

        applied = cursor.fetchall()

        cursor.close()
        conn.close()

        return [(row[0], row[1]) for row in applied]

    except Exception as e:
        print(f"Warning: Could not get applied migrations: {e}")
        return []


def record_migration(migration_name: str, migration_hash: str, execution_time_ms: int):
    """
    Record a successfully applied migration.

    Args:
        migration_name: Name of migration file
        migration_hash: SHA256 hash of migration
        execution_time_ms: Execution time in milliseconds
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO schema_migrations (migration_name, migration_hash, execution_time_ms)
            VALUES (%s, %s, %s)
            ON CONFLICT (migration_name) DO NOTHING
        """, (migration_name, migration_hash, execution_time_ms))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Warning: Could not record migration: {e}")


def run_migration(migration_file: Path, migration_hash: str) -> Optional[int]:
    """
    Run a single migration file.

    Args:
        migration_file: Path to SQL migration file
        migration_hash: SHA256 hash of migration file

    Returns:
        Execution time in milliseconds if successful, None otherwise
    """
    try:
        start_time = datetime.now()

        conn = get_db_connection()
        cursor = conn.cursor()

        # Read migration SQL
        with open(migration_file, 'r') as f:
            sql = f.read()

        # Execute migration
        cursor.execute(sql)
        conn.commit()

        cursor.close()
        conn.close()

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        print(f"✓ Migration applied: {os.path.basename(migration_file)} ({execution_time:.0f}ms)")
        return int(execution_time)

    except Exception as e:
        print(f"✗ Migration failed: {os.path.basename(migration_file)}")
        print(f"  Error: {e}")
        return None


def run_all_migrations() -> int:
    """
    Run all pending migrations in order.

    Returns:
        Number of migrations applied
    """
    # Ensure migrations tracking table exists
    if not ensure_migrations_table():
        return 0

    migrations_dir = Path(__file__).parent / "migrations"

    if not migrations_dir.exists():
        print("No migrations directory found")
        return 0

    # Get all .sql files sorted by name
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        print("No migration files found")
        return 0

    # Get already applied migrations
    applied_migrations = {name: hash_ for name, hash_ in get_applied_migrations()}

    # Filter pending migrations
    pending_migrations = []
    for migration_file in migration_files:
        migration_name = migration_file.name
        migration_hash = get_migration_hash(migration_file)

        if migration_name in applied_migrations:
            # Check if migration file was modified
            if applied_migrations[migration_name] != migration_hash:
                print(f"⚠ Warning: Migration {migration_name} was modified after being applied")
                print(f"  Skipping to avoid inconsistencies")
            continue

        pending_migrations.append((migration_file, migration_hash))

    if not pending_migrations:
        print("All migrations up to date")
        return 0

    print(f"Found {len(migration_files)} total migration(s)")
    print(f"Applying {len(pending_migrations)} pending migration(s)")
    print()

    applied = 0
    for migration_file, migration_hash in pending_migrations:
        execution_time = run_migration(migration_file, migration_hash)

        if execution_time is not None:
            record_migration(migration_file.name, migration_hash, execution_time)
            applied += 1
        else:
            print("Stopping due to error")
            break

    print()
    print(f"Applied {applied}/{len(pending_migrations)} migration(s)")

    return applied


if __name__ == "__main__":
    print("Running database migrations...")
    print()
    run_all_migrations()
