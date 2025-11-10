"""Unit tests for intelligent ranking module."""

import pytest
from datetime import datetime, timedelta
from search.ranking import (
    rerank_results, calculate_title_match_score,
    calculate_recency_score, calculate_quality_score,
    calculate_tag_relevance_score, get_score_explanation
)


class TestRanking:
    """Test intelligent ranking functions."""

    def test_calculate_title_match_score_exact(self):
        """Test title matching with exact match."""
        query = "python function"
        snippet = {'title': 'Python Function Example'}

        score = calculate_title_match_score(snippet, query)

        assert score == 1.0  # All query words in title

    def test_calculate_title_match_score_partial(self):
        """Test title matching with partial match."""
        query = "python function example test"
        snippet = {'title': 'Python Function'}

        score = calculate_title_match_score(snippet, query)

        assert 0 < score < 1.0  # Some query words in title
        assert score == 0.5  # 2 out of 4 words match

    def test_calculate_title_match_score_no_match(self):
        """Test title matching with no match."""
        query = "javascript react"
        snippet = {'title': 'Python Django Tutorial'}

        score = calculate_title_match_score(snippet, query)

        assert score == 0.0

    def test_calculate_recency_score_today(self):
        """Test recency scoring for today's snippet."""
        snippet = {'created_at': datetime.now()}

        score = calculate_recency_score(snippet)

        assert score > 0.99  # Very recent

    def test_calculate_recency_score_old(self):
        """Test recency scoring for old snippet."""
        snippet = {'created_at': datetime.now() - timedelta(days=730)}  # 2 years

        score = calculate_recency_score(snippet)

        assert score < 0.5  # Old snippet

    def test_calculate_recency_score_moderate(self):
        """Test recency scoring for moderately old snippet."""
        snippet = {'created_at': datetime.now() - timedelta(days=180)}  # ~6 months

        score = calculate_recency_score(snippet)

        assert 0.3 < score < 0.9

    def test_calculate_quality_score_high(self):
        """Test quality scoring for high-quality snippet."""
        snippet = {
            'code': 'def complex_function():\n    # Detailed implementation\n    pass',
            'tags': ['python', 'function', 'algorithm'],
            'summary': 'This is a well-documented function'
        }

        score = calculate_quality_score(snippet)

        assert score > 0.7

    def test_calculate_quality_score_low(self):
        """Test quality scoring for low-quality snippet."""
        snippet = {
            'code': 'x=1',  # Very short
            'tags': [],  # No tags
            'summary': None  # No summary
        }

        score = calculate_quality_score(snippet)

        assert score < 0.5

    def test_calculate_quality_score_medium(self):
        """Test quality scoring for medium-quality snippet."""
        snippet = {
            'code': 'print("hello world")',
            'tags': ['python'],
            'summary': None
        }

        score = calculate_quality_score(snippet)

        assert 0.3 < score < 0.8

    def test_calculate_tag_relevance_score_perfect(self):
        """Test tag relevance with all query terms in tags."""
        query = "python api"
        snippet = {'tags': ['python', 'api', 'rest', 'http']}

        score = calculate_tag_relevance_score(snippet, query)

        assert score == 1.0

    def test_calculate_tag_relevance_score_partial(self):
        """Test tag relevance with some query terms in tags."""
        query = "python api database"
        snippet = {'tags': ['python', 'api']}

        score = calculate_tag_relevance_score(snippet, query)

        assert 0 < score < 1.0
        assert abs(score - 0.667) < 0.01  # 2 out of 3

    def test_calculate_tag_relevance_score_none(self):
        """Test tag relevance with no matching tags."""
        query = "javascript react"
        snippet = {'tags': ['python', 'django']}

        score = calculate_tag_relevance_score(snippet, query)

        assert score == 0.0

    def test_calculate_tag_relevance_score_empty_tags(self):
        """Test tag relevance with empty tags."""
        query = "python"
        snippet = {'tags': []}

        score = calculate_tag_relevance_score(snippet, query)

        assert score == 0.0

    def test_rerank_results_ordering(self):
        """Test that rerank_results orders by final score."""
        results = [
            {
                'id': '1',
                'score': 0.5,  # Low vector score
                'snippet': {
                    'id': 1,
                    'title': 'Exact Query Match',  # High title match
                    'code': 'detailed code here',
                    'tags': ['relevant'],
                    'created_at': datetime.now(),
                    'summary': 'Good summary'
                }
            },
            {
                'id': '2',
                'score': 0.9,  # High vector score
                'snippet': {
                    'id': 2,
                    'title': 'Other Title',  # Low title match
                    'code': 'x',
                    'tags': [],
                    'created_at': datetime.now() - timedelta(days=365),
                    'summary': None
                }
            }
        ]

        reranked = rerank_results(results, "exact query match")

        # Results should be reordered based on combined scores
        assert len(reranked) == 2
        assert all('final_score' in r for r in reranked)
        assert all('score_breakdown' in r for r in reranked)
        # First result should have higher final_score
        assert reranked[0]['final_score'] >= reranked[1]['final_score']

    def test_rerank_results_custom_weights(self):
        """Test reranking with custom weights."""
        results = [
            {
                'id': '1',
                'score': 0.8,
                'snippet': {
                    'id': 1,
                    'title': 'Test',
                    'code': 'code',
                    'tags': ['test'],
                    'created_at': datetime.now(),
                    'summary': 'Summary'
                }
            }
        ]

        custom_weights = {
            'hybrid': 0.3,
            'title_match': 0.4,
            'recency': 0.1,
            'quality': 0.1,
            'tags': 0.1
        }

        reranked = rerank_results(results, "test", weights=custom_weights)

        assert len(reranked) == 1
        assert 'score_breakdown' in reranked[0]

    def test_get_score_explanation(self):
        """Test score explanation generation."""
        result = {
            'final_score': 0.85,
            'score_breakdown': {
                'hybrid': 0.9,
                'title_match': 0.8,
                'recency': 0.95,
                'quality': 0.7,
                'tags': 0.6,
                'weights': {
                    'hybrid': 1.0,
                    'title_match': 0.0,
                    'recency': 0.0,
                    'quality': 0.0,
                    'tags': 0.0
                }
            }
        }

        explanation = get_score_explanation(result)

        assert isinstance(explanation, str)
        assert 'hybrid' in explanation.lower()
        assert '0.9' in explanation or '90' in explanation

    def test_rerank_empty_results(self):
        """Test reranking with empty results."""
        reranked = rerank_results([], "query")

        assert reranked == []

    def test_rerank_single_result(self):
        """Test reranking with single result."""
        results = [
            {
                'id': '1',
                'score': 0.8,
                'snippet': {
                    'id': 1,
                    'title': 'Test',
                    'code': 'code',
                    'tags': [],
                    'created_at': datetime.now()
                }
            }
        ]

        reranked = rerank_results(results, "test")

        assert len(reranked) == 1
        assert reranked[0]['final_score'] > 0
