"""
SQLite database adapter for fully local SnipVault setup.

Provides drop-in replacement for PostgreSQL for users who want
a fully local solution without external database dependencies.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime
from utils.logger import get_logger
from utils.exceptions import DatabaseError
from config import get_config

logger = get_logger(__name__)


class SQLiteAdapter:
    """SQLite database adapter."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize SQLite adapter.

        Args:
            db_path: Path to SQLite database file
        """
        if db_path:
            self.db_path = db_path
        else:
            config = get_config()
            path_str = config.get('database.sqlite.path', '~/.snipvault/snipvault.db')
            self.db_path = Path(path_str).expanduser()

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._initialize_database()

    def _initialize_database(self):
        """Initialize database schema."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Create snippets table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS snippets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        code TEXT NOT NULL,
                        language TEXT NOT NULL,
                        tags TEXT,  -- JSON array stored as text
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        summary TEXT,
                        view_count INTEGER DEFAULT 0,
                        last_viewed TIMESTAMP
                    )
                """)

                # Create full-text search virtual table
                cursor.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS snippets_fts USING fts5(
                        title, code, tags,
                        content=snippets,
                        content_rowid=id
                    )
                """)

                # Create triggers to keep FTS in sync
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS snippets_ai AFTER INSERT ON snippets BEGIN
                        INSERT INTO snippets_fts(rowid, title, code, tags)
                        VALUES (new.id, new.title, new.code, new.tags);
                    END
                """)

                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS snippets_ad AFTER DELETE ON snippets BEGIN
                        DELETE FROM snippets_fts WHERE rowid = old.id;
                    END
                """)

                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS snippets_au AFTER UPDATE ON snippets BEGIN
                        DELETE FROM snippets_fts WHERE rowid = old.id;
                        INSERT INTO snippets_fts(rowid, title, code, tags)
                        VALUES (new.id, new.title, new.code, new.tags);
                    END
                """)

                # Create migrations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        migration_name TEXT UNIQUE NOT NULL,
                        migration_hash TEXT NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        execution_time_ms INTEGER
                    )
                """)

                conn.commit()

            logger.info(f"SQLite database initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {e}")
            raise DatabaseError(f"Failed to initialize SQLite database: {e}")

    @contextmanager
    def get_connection(self):
        """
        Get database connection context manager.

        Yields:
            SQLite connection
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"SQLite connection error: {e}")
            raise DatabaseError(f"SQLite connection error: {e}")

        finally:
            if conn:
                conn.close()

    def insert_snippet(
        self,
        title: str,
        code: str,
        language: str,
        tags: Optional[List[str]] = None,
        summary: Optional[str] = None
    ) -> int:
        """
        Insert a new snippet.

        Args:
            title: Snippet title
            code: Code content
            language: Programming language
            tags: Tags list
            summary: AI-generated summary

        Returns:
            Snippet ID
        """
        import json

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                tags_json = json.dumps(tags) if tags else '[]'

                cursor.execute("""
                    INSERT INTO snippets (title, code, language, tags, summary)
                    VALUES (?, ?, ?, ?, ?)
                """, (title, code, language, tags_json, summary))

                snippet_id = cursor.lastrowid
                conn.commit()

                return snippet_id

        except Exception as e:
            logger.error(f"Failed to insert snippet: {e}")
            raise DatabaseError(f"Failed to insert snippet: {e}")

    def get_snippet_by_id(self, snippet_id: int) -> Optional[Dict[str, Any]]:
        """
        Get snippet by ID.

        Args:
            snippet_id: Snippet ID

        Returns:
            Snippet dict or None
        """
        import json

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM snippets WHERE id = ?", (snippet_id,))
                row = cursor.fetchone()

                if not row:
                    return None

                return {
                    'id': row['id'],
                    'title': row['title'],
                    'code': row['code'],
                    'language': row['language'],
                    'tags': json.loads(row['tags']) if row['tags'] else [],
                    'created_at': datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    'summary': row['summary']
                }

        except Exception as e:
            logger.error(f"Failed to get snippet: {e}")
            return None

    def list_all_snippets(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        List all snippets.

        Args:
            limit: Maximum number of snippets

        Returns:
            List of snippet dicts
        """
        import json

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM snippets
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))

                rows = cursor.fetchall()

                return [
                    {
                        'id': row['id'],
                        'title': row['title'],
                        'code': row['code'],
                        'language': row['language'],
                        'tags': json.loads(row['tags']) if row['tags'] else [],
                        'created_at': datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                        'summary': row['summary']
                    }
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Failed to list snippets: {e}")
            return []

    def full_text_search(
        self,
        query: str,
        language: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Perform full-text search.

        Args:
            query: Search query
            language: Language filter
            tags: Tags filter
            limit: Result limit

        Returns:
            List of matching snippets with rank
        """
        import json

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Build query
                sql = """
                    SELECT s.*, rank
                    FROM snippets s
                    JOIN snippets_fts fts ON s.id = fts.rowid
                    WHERE snippets_fts MATCH ?
                """
                params = [query]

                if language:
                    sql += " AND s.language = ?"
                    params.append(language)

                sql += " ORDER BY rank LIMIT ?"
                params.append(limit)

                cursor.execute(sql, params)
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    snippet_tags = json.loads(row['tags']) if row['tags'] else []

                    # Filter by tags if specified
                    if tags and not any(t in snippet_tags for t in tags):
                        continue

                    results.append({
                        'id': row['id'],
                        'title': row['title'],
                        'code': row['code'],
                        'language': row['language'],
                        'tags': snippet_tags,
                        'created_at': datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                        'summary': row['summary'],
                        'rank': row['rank']
                    })

                return results

        except Exception as e:
            logger.error(f"Full-text search failed: {e}")
            return []

    def delete_snippet(self, snippet_id: int) -> bool:
        """
        Delete a snippet.

        Args:
            snippet_id: Snippet ID

        Returns:
            True if deleted
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("DELETE FROM snippets WHERE id = ?", (snippet_id,))
                conn.commit()

                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to delete snippet: {e}")
            return False


# Global adapter instance
_adapter_instance: Optional[SQLiteAdapter] = None


def get_sqlite_adapter() -> SQLiteAdapter:
    """
    Get global SQLite adapter instance.

    Returns:
        SQLiteAdapter instance
    """
    global _adapter_instance

    if _adapter_instance is None:
        _adapter_instance = SQLiteAdapter()

    return _adapter_instance
