"""PostgreSQL full-text search functions for SnipVault."""

from db.setup import get_db_connection


def full_text_search(query, language=None, tags=None, limit=50):
    """
    Perform full-text search on snippets using PostgreSQL.

    Args:
        query: Search query
        language: Optional language filter
        tags: Optional tags filter (list)
        limit: Maximum results to return

    Returns:
        List of snippet dictionaries with rank scores
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Build the search query
        tsquery = ' & '.join(query.split())  # AND search

        # Base query with ranking
        sql = """
            SELECT
                id, title, code, language, tags, created_at,
                ts_rank(search_vector, to_tsquery('english', %s)) as rank
            FROM snippets
            WHERE search_vector @@ to_tsquery('english', %s)
        """

        params = [tsquery, tsquery]

        # Add language filter
        if language:
            sql += " AND language = %s"
            params.append(language)

        # Add tags filter
        if tags:
            sql += " AND tags && %s"
            params.append(tags)

        # Order by rank and limit
        sql += " ORDER BY rank DESC LIMIT %s"
        params.append(limit)

        cursor.execute(sql, params)
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        return results

    except Exception as e:
        print(f"Error in full-text search: {e}")
        return []


def keyword_search_simple(query, limit=50):
    """
    Simple keyword search using ILIKE (case-insensitive pattern matching).
    Fallback when full-text search is not available.

    Args:
        query: Search query
        limit: Maximum results

    Returns:
        List of snippet dictionaries
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        pattern = f"%{query}%"

        sql = """
            SELECT id, title, code, language, tags, created_at,
                   CASE
                       WHEN title ILIKE %s THEN 2.0
                       WHEN code ILIKE %s THEN 1.0
                       ELSE 0.5
                   END as rank
            FROM snippets
            WHERE title ILIKE %s OR code ILIKE %s
            ORDER BY rank DESC, created_at DESC
            LIMIT %s
        """

        cursor.execute(sql, [pattern, pattern, pattern, pattern, limit])
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        return results

    except Exception as e:
        print(f"Error in keyword search: {e}")
        return []


def get_snippet_rank(snippet_id, query):
    """
    Get ranking score for a specific snippet against a query.

    Args:
        snippet_id: Snippet ID
        query: Search query

    Returns:
        Float rank score
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        tsquery = ' & '.join(query.split())

        sql = """
            SELECT ts_rank(search_vector, to_tsquery('english', %s)) as rank
            FROM snippets
            WHERE id = %s
        """

        cursor.execute(sql, [tsquery, snippet_id])
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        return result['rank'] if result else 0.0

    except Exception as e:
        print(f"Error getting snippet rank: {e}")
        return 0.0
