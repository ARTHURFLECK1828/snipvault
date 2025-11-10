"""Unit tests for hybrid search module."""

import pytest
from unittest.mock import patch, MagicMock
from search.hybrid import hybrid_search, merge_search_results, normalize_scores


class TestHybridSearch:
    """Test hybrid search functionality."""

    @patch('search.hybrid.full_text_search')
    @patch('search.hybrid.get_pinecone_index')
    @patch('search.hybrid.generate_query_embedding')
    @patch('search.hybrid.get_snippets_by_ids')
    def test_hybrid_search_basic(self, mock_get_snippets, mock_gen_emb,
                                  mock_get_index, mock_fts, sample_embedding,
                                  sample_snippets):
        """Test basic hybrid search."""
        # Setup mocks
        mock_gen_emb.return_value = sample_embedding
        mock_index = MagicMock()
        mock_index.query.return_value = {
            'matches': [
                {'id': '1', 'score': 0.95},
                {'id': '2', 'score': 0.85}
            ]
        }
        mock_get_index.return_value = mock_index
        mock_fts.return_value = [
            {'id': 1, 'rank': 0.9},
            {'id': 3, 'rank': 0.7}
        ]
        mock_get_snippets.return_value = sample_snippets

        results = hybrid_search("test query", top_k=5)

        assert len(results) > 0
        assert all('snippet' in r for r in results)
        assert all('score' in r for r in results)
        mock_gen_emb.assert_called_once()
        mock_index.query.assert_called_once()
        mock_fts.assert_called_once()

    @patch('search.hybrid.full_text_search')
    @patch('search.hybrid.get_pinecone_index')
    @patch('search.hybrid.generate_query_embedding')
    def test_hybrid_search_with_filters(self, mock_gen_emb, mock_get_index,
                                        mock_fts, sample_embedding):
        """Test hybrid search with language and tag filters."""
        mock_gen_emb.return_value = sample_embedding
        mock_index = MagicMock()
        mock_index.query.return_value = {'matches': []}
        mock_get_index.return_value = mock_index
        mock_fts.return_value = []

        results = hybrid_search(
            "test query",
            language="python",
            tags=["test", "api"],
            top_k=5
        )

        # Verify filters were applied
        call_kwargs = mock_index.query.call_args[1]
        assert 'filter' in call_kwargs
        mock_fts.assert_called_with(
            "test query",
            language="python",
            tags=["test", "api"],
            limit=50
        )

    def test_normalize_scores_empty(self):
        """Test score normalization with empty results."""
        normalized = normalize_scores({})
        assert normalized == {}

    def test_normalize_scores_single_result(self):
        """Test score normalization with single result."""
        scores = {1: 0.5}
        normalized = normalize_scores(scores)
        assert normalized[1] == 1.0  # Single score normalized to 1.0

    def test_normalize_scores_multiple_results(self):
        """Test score normalization with multiple results."""
        scores = {1: 0.9, 2: 0.6, 3: 0.3}
        normalized = normalize_scores(scores)

        # Check all scores are between 0 and 1
        assert all(0 <= v <= 1 for v in normalized.values())
        # Highest score should be 1.0
        assert max(normalized.values()) == 1.0
        # Relative order should be preserved
        assert normalized[1] > normalized[2] > normalized[3]

    @patch('search.hybrid.get_snippets_by_ids')
    def test_merge_search_results(self, mock_get_snippets, sample_snippets):
        """Test merging vector and keyword search results."""
        mock_get_snippets.return_value = sample_snippets

        vector_scores = {1: 0.95, 2: 0.85}
        keyword_scores = {1: 0.80, 3: 0.70}

        results = merge_search_results(
            vector_scores,
            keyword_scores,
            vector_weight=0.6,
            keyword_weight=0.4
        )

        assert len(results) == 3  # IDs 1, 2, 3
        # ID 1 appears in both, should have highest combined score
        assert results[0]['id'] == '1'

    @patch('search.hybrid.enhance_query')
    @patch('search.hybrid.generate_query_embedding')
    def test_hybrid_search_no_enhancement(self, mock_gen_emb, mock_enhance,
                                          sample_embedding):
        """Test hybrid search without query enhancement."""
        mock_gen_emb.return_value = sample_embedding

        with patch('search.hybrid.full_text_search') as mock_fts, \
             patch('search.hybrid.get_pinecone_index') as mock_index:
            mock_fts.return_value = []
            mock_idx = MagicMock()
            mock_idx.query.return_value = {'matches': []}
            mock_index.return_value = mock_idx

            hybrid_search("query", use_enhancement=False)

            mock_enhance.assert_not_called()
            mock_gen_emb.assert_called_with("query")

    @patch('search.hybrid.enhance_query')
    @patch('search.hybrid.generate_query_embedding')
    def test_hybrid_search_with_enhancement(self, mock_gen_emb, mock_enhance,
                                            sample_embedding):
        """Test hybrid search with query enhancement."""
        mock_enhance.return_value = "enhanced query"
        mock_gen_emb.return_value = sample_embedding

        with patch('search.hybrid.full_text_search') as mock_fts, \
             patch('search.hybrid.get_pinecone_index') as mock_index:
            mock_fts.return_value = []
            mock_idx = MagicMock()
            mock_idx.query.return_value = {'matches': []}
            mock_index.return_value = mock_idx

            hybrid_search("query", use_enhancement=True)

            mock_enhance.assert_called_once_with("query")
            mock_gen_emb.assert_called_with("enhanced query")
