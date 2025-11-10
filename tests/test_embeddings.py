"""Unit tests for LLM embeddings module."""

import pytest
from unittest.mock import patch, MagicMock
from llm.embeddings import generate_embedding, generate_query_embedding, generate_batch_embeddings


class TestEmbeddings:
    """Test embedding generation functions."""

    @patch('llm.embeddings.genai')
    def test_generate_embedding_success(self, mock_genai, sample_embedding):
        """Test successful embedding generation."""
        mock_result = MagicMock()
        mock_result.embedding = sample_embedding
        mock_genai.embed_content.return_value = mock_result

        result = generate_embedding("test code snippet")

        assert result == sample_embedding
        assert len(result) == 768
        mock_genai.embed_content.assert_called_once()

    @patch('llm.embeddings.genai')
    def test_generate_embedding_empty_text(self, mock_genai):
        """Test embedding generation with empty text."""
        result = generate_embedding("")

        assert result is None
        mock_genai.embed_content.assert_not_called()

    @patch('llm.embeddings.genai')
    def test_generate_embedding_api_error(self, mock_genai):
        """Test embedding generation with API error."""
        mock_genai.embed_content.side_effect = Exception("API Error")

        result = generate_embedding("test code")

        assert result is None

    @patch('llm.embeddings.genai')
    def test_generate_query_embedding(self, mock_genai, sample_embedding):
        """Test query embedding generation."""
        mock_result = MagicMock()
        mock_result.embedding = sample_embedding
        mock_genai.embed_content.return_value = mock_result

        result = generate_query_embedding("search query")

        assert result == sample_embedding
        mock_genai.embed_content.assert_called_once()

    @patch('llm.embeddings.genai')
    def test_generate_batch_embeddings(self, mock_genai, sample_embedding):
        """Test batch embedding generation."""
        mock_result = MagicMock()
        mock_result.embedding = sample_embedding
        mock_genai.embed_content.return_value = mock_result

        texts = ["snippet 1", "snippet 2", "snippet 3"]
        results = generate_batch_embeddings(texts)

        assert len(results) == 3
        assert all(r == sample_embedding for r in results)
        assert mock_genai.embed_content.call_count == 3

    @patch('llm.embeddings.genai')
    def test_generate_batch_embeddings_with_failures(self, mock_genai, sample_embedding):
        """Test batch embedding with some failures."""
        mock_result = MagicMock()
        mock_result.embedding = sample_embedding

        # First call succeeds, second fails, third succeeds
        mock_genai.embed_content.side_effect = [
            mock_result,
            Exception("API Error"),
            mock_result
        ]

        texts = ["snippet 1", "snippet 2", "snippet 3"]
        results = generate_batch_embeddings(texts)

        assert len(results) == 3
        assert results[0] == sample_embedding
        assert results[1] is None
        assert results[2] == sample_embedding
