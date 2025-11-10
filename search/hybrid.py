"""Hybrid search combining vector and keyword search."""

from db.full_text import full_text_search
from db.setup import get_pinecone_index
from db.queries import get_snippets_by_ids
from llm.embeddings import generate_query_embedding
from llm.query_enhancer import enhance_query


def normalize_score(score, min_val, max_val):
    """Normalize score to 0-1 range."""
    if max_val == min_val:
        return 0.5
    return (score - min_val) / (max_val - min_val)


def normalize_scores(scores):
    """
    Normalize a dictionary of scores to 0-1 range.

    Args:
        scores: Dict of {id: score}

    Returns:
        Dict of {id: normalized_score}
    """
    if not scores:
        return {}

    if len(scores) == 1:
        # Single score normalized to 1.0
        return {k: 1.0 for k in scores.keys()}

    min_score = min(scores.values())
    max_score = max(scores.values())

    if max_score == min_score:
        return {k: 1.0 for k in scores.keys()}

    return {
        k: (v - min_score) / (max_score - min_score)
        for k, v in scores.items()
    }


def merge_search_results(vector_scores, keyword_scores, vector_weight=0.6, keyword_weight=0.4):
    """
    Merge vector and keyword search results with weighted scoring.

    Args:
        vector_scores: Dict of {id: vector_score}
        keyword_scores: Dict of {id: keyword_score}
        vector_weight: Weight for vector scores (default 0.6)
        keyword_weight: Weight for keyword scores (default 0.4)

    Returns:
        List of result dicts sorted by combined score
    """
    # Normalize weights
    total_weight = vector_weight + keyword_weight
    vector_weight = vector_weight / total_weight
    keyword_weight = keyword_weight / total_weight

    # Normalize scores
    vector_norm = normalize_scores(vector_scores)
    keyword_norm = normalize_scores(keyword_scores)

    # Combine all IDs
    all_ids = set(vector_scores.keys()) | set(keyword_scores.keys())

    if not all_ids:
        return []

    # Calculate combined scores
    combined_results = []
    for snippet_id in all_ids:
        vector_score = vector_norm.get(snippet_id, 0)
        keyword_score = keyword_norm.get(snippet_id, 0)

        combined_score = (
            vector_weight * vector_score +
            keyword_weight * keyword_score
        )

        combined_results.append({
            'id': str(snippet_id),
            'score': combined_score,
            'vector_score': vector_scores.get(snippet_id, 0),
            'keyword_score': keyword_scores.get(snippet_id, 0)
        })

    # Sort by combined score
    combined_results.sort(key=lambda x: x['score'], reverse=True)

    # Get snippet details
    snippet_ids = [r['id'] for r in combined_results]
    snippets = get_snippets_by_ids(snippet_ids)
    snippet_dict = {str(s['id']): s for s in snippets}

    # Add snippet data to results
    for result in combined_results:
        if result['id'] in snippet_dict:
            result['snippet'] = snippet_dict[result['id']]

    return combined_results


def hybrid_search(query, top_k=10, use_enhancement=True,
                  vector_weight=0.6, keyword_weight=0.4,
                  language=None, tags=None):
    """
    Perform hybrid search combining vector and keyword search.

    Args:
        query: Search query
        top_k: Number of results to return
        use_enhancement: Whether to use LLM query enhancement
        vector_weight: Weight for vector search score (0-1)
        keyword_weight: Weight for keyword search score (0-1)
        language: Optional language filter
        tags: Optional tags filter

    Returns:
        List of result dictionaries with combined scores
    """
    # Normalize weights
    total_weight = vector_weight + keyword_weight
    vector_weight = vector_weight / total_weight
    keyword_weight = keyword_weight / total_weight

    # Enhance query if requested
    search_query = enhance_query(query) if use_enhancement else query

    # 1. Vector search
    embedding = generate_query_embedding(search_query)
    if not embedding:
        # Fall back to keyword-only search
        return keyword_only_search(query, top_k, language, tags)

    index = get_pinecone_index()

    # Build Pinecone filters
    filters = {}
    if language:
        filters['language'] = {'$eq': language}
    if tags:
        tag_list = tags if isinstance(tags, list) else [tags]
        filters['tags'] = {'$in': tag_list}

    query_params = {
        'vector': embedding,
        'top_k': 50,  # Get more for merging
        'include_metadata': True
    }
    if filters:
        query_params['filter'] = filters

    vector_results = index.query(**query_params)

    # 2. Keyword search
    keyword_results = full_text_search(
        query,
        language=language,
        tags=tags,
        limit=50
    )

    # 3. Build score dictionaries
    vector_scores = {
        match['id']: match['score']
        for match in vector_results.get('matches', [])
    }

    keyword_scores = {
        str(result['id']): result.get('rank', 0)
        for result in keyword_results
    }

    # 4. Merge results
    all_ids = set(vector_scores.keys()) | set(keyword_scores.keys())

    if not all_ids:
        return []

    # Find min/max for normalization
    vector_min = min(vector_scores.values()) if vector_scores else 0
    vector_max = max(vector_scores.values()) if vector_scores else 1
    keyword_min = min(keyword_scores.values()) if keyword_scores else 0
    keyword_max = max(keyword_scores.values()) if keyword_scores else 1

    combined_results = []
    for snippet_id in all_ids:
        vector_score = vector_scores.get(snippet_id, 0)
        keyword_score = keyword_scores.get(snippet_id, 0)

        # Normalize scores
        vector_norm = normalize_score(vector_score, vector_min, vector_max)
        keyword_norm = normalize_score(keyword_score, keyword_min, keyword_max)

        # Weighted combination
        combined_score = (
            vector_weight * vector_norm +
            keyword_weight * keyword_norm
        )

        combined_results.append({
            'id': snippet_id,
            'score': combined_score,
            'vector_score': vector_score,
            'keyword_score': keyword_score,
            'vector_norm': vector_norm,
            'keyword_norm': keyword_norm
        })

    # Sort by combined score
    combined_results.sort(key=lambda x: x['score'], reverse=True)

    # Get snippet details
    result_ids = [r['id'] for r in combined_results[:top_k * 2]]
    snippets = get_snippets_by_ids(result_ids)
    snippet_dict = {str(s['id']): s for s in snippets}

    # Add snippet data to results
    final_results = []
    for result in combined_results[:top_k * 2]:
        if result['id'] in snippet_dict:
            result['snippet'] = snippet_dict[result['id']]
            final_results.append(result)

    return final_results


def keyword_only_search(query, top_k, language=None, tags=None):
    """
    Fallback to keyword-only search if vector search fails.

    Args:
        query: Search query
        top_k: Number of results
        language: Language filter
        tags: Tags filter

    Returns:
        List of results
    """
    results = full_text_search(query, language=language, tags=tags, limit=top_k)

    return [
        {
            'id': str(r['id']),
            'score': r.get('rank', 0),
            'vector_score': 0,
            'keyword_score': r.get('rank', 0)
        }
        for r in results
    ]
