"""Intelligent result ranking with multiple factors."""

import math
from datetime import datetime
from db.queries import get_snippets_by_ids


def calculate_title_match_score(snippet, query):
    """
    Calculate title match score based on query terms in title.

    Args:
        snippet: Snippet dict with 'title' field
        query: Search query string

    Returns:
        Score between 0 and 1
    """
    query_terms = set(query.lower().split())
    if not query_terms:
        return 0.0

    title_words = set(snippet['title'].lower().split())
    title_overlap = len(query_terms & title_words)

    # Calculate base score
    score = title_overlap / len(query_terms)

    # Boost if ALL query terms in title
    if query_terms.issubset(title_words):
        score = min(1.0, score * 1.5)

    return score


def calculate_recency_score(snippet):
    """
    Calculate recency score based on snippet age.

    Args:
        snippet: Snippet dict with 'created_at' field

    Returns:
        Score between 0 and 1 (newer = higher)
    """
    days_old = (datetime.now() - snippet['created_at']).days

    # Exponential decay: full score for <30 days, half at ~365 days
    recency_score = math.exp(-days_old / 365)

    return recency_score


def calculate_quality_score(snippet):
    """
    Calculate quality score based on code quality indicators.

    Args:
        snippet: Snippet dict with 'code', 'tags', 'summary' fields

    Returns:
        Score between 0 and 1
    """
    quality_indicators = []

    # Has substantial code (> 50 lines or > 300 chars)
    lines = len(snippet['code'].split('\n'))
    code_length = len(snippet['code'])
    has_substance = lines > 50 or code_length > 300
    quality_indicators.append(1.0 if has_substance else 0.3)

    # Has tags
    has_tags = len(snippet.get('tags', [])) > 0
    quality_indicators.append(1.0 if has_tags else 0.2)

    # Has summary (if available)
    has_summary = snippet.get('summary') is not None
    quality_indicators.append(1.0 if has_summary else 0.3)

    # Code not too long (< 500 lines)
    reasonable_length = lines < 500
    quality_indicators.append(1.0 if reasonable_length else 0.7)

    return sum(quality_indicators) / len(quality_indicators)


def calculate_tag_relevance_score(snippet, query):
    """
    Calculate tag relevance score based on query terms in tags.

    Args:
        snippet: Snippet dict with 'tags' field
        query: Search query string

    Returns:
        Score between 0 and 1
    """
    query_terms = set(query.lower().split())
    if not query_terms:
        return 0.0

    tags = snippet.get('tags', [])
    if not tags:
        return 0.0

    # Convert tags to lowercase for comparison
    tag_set = set(tag.lower() for tag in tags)

    # Count how many query terms appear in tags
    matching_terms = len(query_terms & tag_set)

    return matching_terms / len(query_terms)


def rerank_results(results, query, weights=None):
    """
    Re-rank search results using multiple factors.

    Args:
        results: List of result dicts from hybrid search
        query: Original search query
        weights: Dict of ranking weights

    Returns:
        Re-ranked list of results with final scores
    """
    if not results:
        return []

    # Default weights
    if weights is None:
        weights = {
            'hybrid': 0.50,      # Hybrid search score
            'title_match': 0.20, # Title keyword matches
            'recency': 0.15,     # How recent the snippet is
            'quality': 0.10,     # Code quality indicators
            'tags': 0.05         # Tag richness
        }

    # Normalize weights
    total = sum(weights.values())
    weights = {k: v/total for k, v in weights.items()}

    # Get snippet details
    snippet_ids = [r['id'] for r in results]
    snippets = get_snippets_by_ids(snippet_ids)
    snippet_dict = {str(s['id']): s for s in snippets}

    # Parse query terms
    query_terms = set(query.lower().split())

    # Calculate additional scores
    for result in results:
        snippet = snippet_dict.get(result['id'])
        if not snippet:
            continue

        # 1. Title match score
        title_words = set(snippet['title'].lower().split())
        title_overlap = len(query_terms & title_words)
        title_score = title_overlap / len(query_terms) if query_terms else 0

        # Boost if ALL query terms in title
        if query_terms.issubset(title_words):
            title_score = min(1.0, title_score * 1.5)

        # 2. Recency score (exponential decay)
        days_old = (datetime.now() - snippet['created_at']).days
        # Decay factor: newer = higher score
        # Full score for <30 days, half at ~365 days
        recency_score = math.exp(-days_old / 365)

        # 3. Quality score
        quality_indicators = []

        # Has substantial code (> 50 lines or > 300 chars)
        lines = len(snippet['code'].split('\n'))
        code_length = len(snippet['code'])
        has_substance = lines > 50 or code_length > 300
        quality_indicators.append(1.0 if has_substance else 0.5)

        # Has tags
        has_tags = len(snippet.get('tags', [])) > 0
        quality_indicators.append(1.0 if has_tags else 0.3)

        # Has summary (if available)
        has_summary = snippet.get('summary') is not None
        quality_indicators.append(1.0 if has_summary else 0.5)

        # Code not too long (< 500 lines)
        reasonable_length = lines < 500
        quality_indicators.append(1.0 if reasonable_length else 0.7)

        quality_score = sum(quality_indicators) / len(quality_indicators)

        # 4. Tags score (more tags = better organized)
        tag_count = len(snippet.get('tags', []))
        tags_score = min(1.0, tag_count / 5)  # Max out at 5 tags

        # 5. Compute final score
        result['final_score'] = (
            weights['hybrid'] * result['score'] +
            weights['title_match'] * title_score +
            weights['recency'] * recency_score +
            weights['quality'] * quality_score +
            weights['tags'] * tags_score
        )

        # Store breakdown for debugging
        result['score_breakdown'] = {
            'hybrid': result['score'],
            'title_match': title_score,
            'recency': recency_score,
            'quality': quality_score,
            'tags': tags_score,
            'weights': weights
        }

        # Store snippet for easy access
        result['snippet'] = snippet

    # Sort by final score
    results.sort(key=lambda x: x['final_score'], reverse=True)

    return results


def get_score_explanation(result):
    """
    Generate human-readable explanation of score.

    Args:
        result: Result dict with score_breakdown

    Returns:
        String explanation
    """
    if 'score_breakdown' not in result:
        return "Score not available"

    breakdown = result['score_breakdown']
    weights = breakdown.get('weights', {})

    parts = []

    # Hybrid score
    hybrid = breakdown.get('hybrid', 0) * weights.get('hybrid', 0)
    parts.append(f"Hybrid: {hybrid:.1%}")

    # Title match
    title = breakdown.get('title_match', 0) * weights.get('title_match', 0)
    if title > 0.01:
        parts.append(f"Title match: {title:.1%}")

    # Recency
    recency = breakdown.get('recency', 0) * weights.get('recency', 0)
    if recency > 0.01:
        parts.append(f"Recent: {recency:.1%}")

    return " + ".join(parts) + f" = {result.get('final_score', 0):.1%}"
