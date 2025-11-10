"""Database query functions for SnipVault."""

from db.setup import get_db_connection


def insert_snippet(title, code, language, tags, summary=None):
    """
    Insert a new snippet into PostgreSQL.

    Args:
        title: Snippet title
        code: Code content
        language: Programming language
        tags: List of tags
        summary: Optional summary of the snippet

    Returns:
        Snippet ID if successful, None otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if summary is not None:
            query = """
                INSERT INTO snippets (title, code, language, tags, summary)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
            """
            cursor.execute(query, (title, code, language, tags, summary))
        else:
            query = """
                INSERT INTO snippets (title, code, language, tags)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """
            cursor.execute(query, (title, code, language, tags))

        snippet_id = cursor.fetchone()['id']

        conn.commit()
        cursor.close()
        conn.close()

        return snippet_id
    except Exception as e:
        print(f"Error inserting snippet: {e}")
        return None


def get_snippets_by_ids(snippet_ids):
    """
    Fetch snippets from PostgreSQL by their IDs.

    Args:
        snippet_ids: List of snippet IDs

    Returns:
        List of snippet dictionaries
    """
    if not snippet_ids:
        return []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Convert IDs to integers
        ids = [int(sid) for sid in snippet_ids]

        query = """
            SELECT id, title, code, language, tags, created_at
            FROM snippets
            WHERE id = ANY(%s)
            ORDER BY created_at DESC;
        """

        cursor.execute(query, (ids,))
        snippets = cursor.fetchall()

        cursor.close()
        conn.close()

        return snippets
    except Exception as e:
        print(f"Error fetching snippets: {e}")
        return []


def get_snippet_by_id(snippet_id):
    """
    Fetch a single snippet by ID.

    Args:
        snippet_id: Snippet ID

    Returns:
        Snippet dictionary or None
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT id, title, code, language, tags, created_at
            FROM snippets
            WHERE id = %s;
        """

        cursor.execute(query, (snippet_id,))
        snippet = cursor.fetchone()

        cursor.close()
        conn.close()

        return snippet
    except Exception as e:
        print(f"Error fetching snippet: {e}")
        return None


def list_all_snippets(limit=100):
    """
    List all snippets from PostgreSQL.

    Args:
        limit: Maximum number of snippets to return

    Returns:
        List of snippet dictionaries
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT id, title, code, language, tags, created_at
            FROM snippets
            ORDER BY created_at DESC
            LIMIT %s;
        """

        cursor.execute(query, (limit,))
        snippets = cursor.fetchall()

        cursor.close()
        conn.close()

        return snippets
    except Exception as e:
        print(f"Error listing snippets: {e}")
        return []


def delete_snippet(snippet_id):
    """
    Delete a snippet from PostgreSQL.

    Args:
        snippet_id: Snippet ID to delete

    Returns:
        True if successful, False if not found or error
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "DELETE FROM snippets WHERE id = %s;"
        cursor.execute(query, (snippet_id,))

        # Check if any rows were deleted
        rows_deleted = cursor.rowcount

        conn.commit()
        cursor.close()
        conn.close()

        return rows_deleted > 0
    except Exception as e:
        print(f"Error deleting snippet: {e}")
        return False


def update_snippet(snippet_id, title=None, code=None, language=None, tags=None, summary=None):
    """
    Update a snippet in PostgreSQL.

    Args:
        snippet_id: Snippet ID to update
        title: New title (optional)
        code: New code (optional)
        language: New language (optional)
        tags: New tags list (optional)
        summary: New summary (optional)

    Returns:
        True if successful, False otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Build dynamic UPDATE query based on provided fields
        updates = []
        values = []

        if title is not None:
            updates.append("title = %s")
            values.append(title)

        if code is not None:
            updates.append("code = %s")
            values.append(code)

        if language is not None:
            updates.append("language = %s")
            values.append(language)

        if tags is not None:
            updates.append("tags = %s")
            values.append(tags)

        if summary is not None:
            updates.append("summary = %s")
            values.append(summary)

        if not updates:
            # Nothing to update
            cursor.close()
            conn.close()
            return True

        # Add snippet_id at the end for WHERE clause
        values.append(snippet_id)

        query = f"UPDATE snippets SET {', '.join(updates)} WHERE id = %s;"
        cursor.execute(query, values)

        conn.commit()
        cursor.close()
        conn.close()

        return True
    except Exception as e:
        print(f"Error updating snippet: {e}")
        return False
