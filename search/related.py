"""Find related snippets based on similarity."""

from db.queries import get_snippet_by_id, get_snippets_by_ids
from db.setup import get_pinecone_index


def get_related_snippets(snippet_id, top_k=5, same_language=True, same_tags=False):
    """
    Find snippets related to the given snippet using vector similarity.

    Args:
        snippet_id: Target snippet ID
        top_k: Number of related snippets to return
        same_language: Only return snippets in same language
        same_tags: Prefer snippets with overlapping tags

    Returns:
        List of related snippet dictionaries
    """
    try:
        # Get original snippet
        snippet = get_snippet_by_id(snippet_id)
        if not snippet:
            return []

        # Get embedding from Pinecone
        index = get_pinecone_index()
        vector_data = index.fetch(ids=[str(snippet_id)])

        if not vector_data.get('vectors') or str(snippet_id) not in vector_data['vectors']:
            # Snippet not in Pinecone, can't find related
            return []

        embedding = vector_data['vectors'][str(snippet_id)]['values']

        # Build filters
        filters = {}
        if same_language:
            filters['language'] = {'$eq': snippet['language']}

        # Search for similar vectors
        query_params = {
            'vector': embedding,
            'top_k': top_k + 1,  # +1 to account for self
            'include_metadata': True
        }

        if filters:
            query_params['filter'] = filters

        results = index.query(**query_params)

        # Exclude self and extract IDs
        related_ids = [
            match['id']
            for match in results.get('matches', [])
            if match['id'] != str(snippet_id)
        ][:top_k]

        if not related_ids:
            return []

        # Get full snippet details
        related_snippets = get_snippets_by_ids(related_ids)

        # If same_tags requested, boost snippets with tag overlap
        if same_tags and snippet.get('tags'):
            original_tags = set(snippet['tags'])

            for related in related_snippets:
                related_tags = set(related.get('tags', []))
                overlap = len(original_tags & related_tags)
                related['tag_overlap'] = overlap

            # Sort by tag overlap (but keep top matches)
            related_snippets.sort(key=lambda x: x.get('tag_overlap', 0), reverse=True)

        return related_snippets

    except Exception as e:
        print(f"Error finding related snippets: {e}")
        return []


def get_similar_by_code(code, language, top_k=5):
    """
    Find snippets similar to provided code (without saving it).

    Args:
        code: Code to find similar snippets for
        language: Programming language
        top_k: Number of results

    Returns:
        List of similar snippets
    """
    try:
        from llm.embeddings import prepare_snippet_text, generate_embedding

        # Generate embedding for the code
        snippet_text = prepare_snippet_text("", code, [])
        embedding = generate_embedding(snippet_text)

        if not embedding:
            return []

        # Search Pinecone
        index = get_pinecone_index()

        query_params = {
            'vector': embedding,
            'top_k': top_k,
            'filter': {'language': {'$eq': language}},
            'include_metadata': True
        }

        results = index.query(**query_params)

        # Get snippet details
        snippet_ids = [match['id'] for match in results.get('matches', [])]
        snippets = get_snippets_by_ids(snippet_ids)

        return snippets

    except Exception as e:
        print(f"Error finding similar code: {e}")
        return []
