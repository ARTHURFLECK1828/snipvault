"""Unit tests for database queries module."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from db.queries import (
    insert_snippet, get_snippet_by_id, get_snippets_by_ids,
    list_all_snippets, update_snippet, delete_snippet
)


class TestDatabaseQueries:
    """Test database query functions."""

    @patch('db.queries.get_db_connection')
    def test_insert_snippet_success(self, mock_get_conn, mock_db_connection):
        """Test successful snippet insertion."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchone.return_value = {'id': 42}  # Returned snippet ID as dict

        snippet_id = insert_snippet(
            title="Test Snippet",
            code="print('test')",
            language="python",
            tags=["test", "python"]
        )

        assert snippet_id == 42
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch('db.queries.get_db_connection')
    def test_insert_snippet_with_summary(self, mock_get_conn, mock_db_connection):
        """Test snippet insertion with summary."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchone.return_value = {'id': 1}  # Returned as dict

        snippet_id = insert_snippet(
            title="Test",
            code="code",
            language="python",
            tags=["test"],
            summary="This is a test snippet"
        )

        assert snippet_id == 1
        call_args = mock_cursor.execute.call_args[0]
        assert 'summary' in call_args[0].lower()

    @patch('db.queries.get_db_connection')
    def test_get_snippet_by_id_found(self, mock_get_conn, mock_db_connection, sample_snippet):
        """Test retrieving an existing snippet by ID."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchone.return_value = {
            'id': sample_snippet['id'],
            'title': sample_snippet['title'],
            'code': sample_snippet['code'],
            'language': sample_snippet['language'],
            'tags': sample_snippet['tags'],
            'created_at': datetime.fromisoformat(sample_snippet['created_at']),
            'summary': sample_snippet.get('summary')
        }

        result = get_snippet_by_id(1)

        assert result is not None
        assert result['id'] == sample_snippet['id']
        assert result['title'] == sample_snippet['title']
        assert result['language'] == sample_snippet['language']

    @patch('db.queries.get_db_connection')
    def test_get_snippet_by_id_not_found(self, mock_get_conn, mock_db_connection):
        """Test retrieving a non-existent snippet."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchone.return_value = None

        result = get_snippet_by_id(999)

        assert result is None

    @patch('db.queries.get_db_connection')
    def test_get_snippets_by_ids(self, mock_get_conn, mock_db_connection, sample_snippets):
        """Test retrieving multiple snippets by IDs."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchall.return_value = [
            {
                'id': s['id'],
                'title': s['title'],
                'code': s['code'],
                'language': s['language'],
                'tags': s['tags'],
                'created_at': s['created_at'],
                'summary': s.get('summary')
            }
            for s in sample_snippets
        ]

        result = get_snippets_by_ids([1, 2, 3])

        assert len(result) == 3
        assert result[0]['id'] == 1
        assert result[1]['id'] == 2

    @patch('db.queries.get_db_connection')
    def test_list_all_snippets(self, mock_get_conn, mock_db_connection, sample_snippets):
        """Test listing all snippets."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchall.return_value = [
            {
                'id': s['id'],
                'title': s['title'],
                'code': s['code'],
                'language': s['language'],
                'tags': s['tags'],
                'created_at': s['created_at'],
                'summary': s.get('summary')
            }
            for s in sample_snippets
        ]

        result = list_all_snippets(limit=100)

        assert len(result) == 3
        mock_cursor.execute.assert_called_once()

    @patch('db.queries.get_db_connection')
    def test_update_snippet_title(self, mock_get_conn, mock_db_connection):
        """Test updating snippet title."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn
        mock_cursor.rowcount = 1

        result = update_snippet(1, title="New Title")

        assert result is True
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch('db.queries.get_db_connection')
    def test_update_snippet_multiple_fields(self, mock_get_conn, mock_db_connection):
        """Test updating multiple snippet fields."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn
        mock_cursor.rowcount = 1

        result = update_snippet(
            1,
            title="New Title",
            code="new code",
            tags=["new", "tags"]
        )

        assert result is True
        call_args = mock_cursor.execute.call_args[0]
        assert 'title' in call_args[0].lower()
        assert 'code' in call_args[0].lower()

    @patch('db.queries.get_db_connection')
    def test_delete_snippet_success(self, mock_get_conn, mock_db_connection):
        """Test successful snippet deletion."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn
        mock_cursor.rowcount = 1

        result = delete_snippet(1)

        assert result is True
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch('db.queries.get_db_connection')
    def test_delete_snippet_not_found(self, mock_get_conn, mock_db_connection):
        """Test deleting a non-existent snippet."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn
        mock_cursor.rowcount = 0

        result = delete_snippet(999)

        assert result is False
