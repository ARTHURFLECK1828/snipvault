"""Pytest configuration and shared fixtures for SnipVault tests."""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock
import psycopg2


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv('POSTGRES_HOST', 'localhost')
    monkeypatch.setenv('POSTGRES_PORT', '5432')
    monkeypatch.setenv('POSTGRES_DB', 'test_snipvault')
    monkeypatch.setenv('POSTGRES_USER', 'test_user')
    monkeypatch.setenv('POSTGRES_PASSWORD', 'test_password')
    monkeypatch.setenv('PINECONE_API_KEY', 'test_pinecone_key')
    monkeypatch.setenv('PINECONE_ENVIRONMENT', 'test_env')
    monkeypatch.setenv('GEMINI_API_KEY', 'test_gemini_key')


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_snippet():
    """Return a sample snippet for testing."""
    return {
        'id': 1,
        'title': 'Test Function',
        'code': 'def hello():\n    return "world"',
        'language': 'python',
        'tags': ['test', 'function'],
        'created_at': '2024-01-01 00:00:00',
        'summary': 'A simple test function'
    }


@pytest.fixture
def sample_snippets():
    """Return multiple sample snippets for testing."""
    from datetime import datetime
    return [
        {
            'id': 1,
            'title': 'Python Hello World',
            'code': 'print("Hello, World!")',
            'language': 'python',
            'tags': ['python', 'basic'],
            'created_at': datetime(2024, 1, 1, 0, 0, 0)
        },
        {
            'id': 2,
            'title': 'JavaScript Alert',
            'code': 'alert("Hello!");',
            'language': 'javascript',
            'tags': ['javascript', 'browser'],
            'created_at': datetime(2024, 1, 2, 0, 0, 0)
        },
        {
            'id': 3,
            'title': 'SQL Query',
            'code': 'SELECT * FROM users WHERE active = true;',
            'language': 'sql',
            'tags': ['sql', 'database'],
            'created_at': datetime(2024, 1, 3, 0, 0, 0)
        }
    ]


@pytest.fixture
def mock_db_connection():
    """Mock database connection with RealDictCursor behavior."""
    from unittest.mock import MagicMock

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Configure cursor to behave like RealDictCursor
    # fetchone and fetchall should return dicts, not tuples
    mock_cursor.fetchone = MagicMock()
    mock_cursor.fetchall = MagicMock()

    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


@pytest.fixture
def mock_pinecone_index():
    """Mock Pinecone index."""
    mock_index = MagicMock()
    mock_index.query.return_value = {
        'matches': [
            {'id': '1', 'score': 0.95, 'metadata': {'language': 'python'}},
            {'id': '2', 'score': 0.85, 'metadata': {'language': 'javascript'}}
        ]
    }
    mock_index.upsert.return_value = {'upserted_count': 1}
    mock_index.delete.return_value = {}
    return mock_index


@pytest.fixture
def mock_gemini_model():
    """Mock Gemini AI model."""
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Enhanced query for testing"
    mock_model.generate_content.return_value = mock_response
    return mock_model


@pytest.fixture
def sample_embedding():
    """Return a sample embedding vector."""
    return [0.1] * 768  # Gemini text-embedding-004 is 768 dimensions


@pytest.fixture
def mock_embedding_function(sample_embedding):
    """Mock embedding generation function."""
    def _generate_embedding(text):
        return sample_embedding
    return _generate_embedding
