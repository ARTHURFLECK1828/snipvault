"""Fuzzy search with typo tolerance."""

import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def correct_query_typos(query):
    """
    Use LLM to correct typos in search query.

    Args:
        query: Original query (possibly with typos)

    Returns:
    Corrected query
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')

        prompt = f"""Check if this search query has typos and correct them.
Only return the corrected query, nothing else.
If no typos detected, return the original query exactly as is.

Query: {query}

Corrected query:"""

        response = model.generate_content(prompt)
        corrected = response.text.strip()

        # Remove any quotes or extra formatting
        corrected = corrected.strip('"\'').strip()

        return corrected if corrected else query

    except Exception as e:
        print(f"Error correcting typos: {e}")
        return query


def fuzzy_search(query, search_func, threshold=0.3, **search_kwargs):
    """
    Perform search with typo tolerance.

    Args:
        query: Search query (possibly with typos)
        search_func: Function to perform actual search (e.g., hybrid_search)
        threshold: Minimum score to consider results valid
        **search_kwargs: Additional args to pass to search_func

    Returns:
        Dict with results and optional suggestion
    """
    # Try normal search first
    results = search_func(query, **search_kwargs)

    # Check if results are poor quality
    needs_correction = (
        not results or
        (results and results[0].get('score', 0) < threshold)
    )

    if needs_correction:
        # Try typo correction
        corrected = correct_query_typos(query)

        if corrected.lower() != query.lower():
            # Search with corrected query
            corrected_results = search_func(corrected, **search_kwargs)

            # Use corrected results if they're better
            if corrected_results and (
                not results or
                corrected_results[0].get('score', 0) > results[0].get('score', 0)
            ):
                return {
                    'results': corrected_results,
                    'suggestion': f"Showing results for '{corrected}'",
                    'original_query': query,
                    'corrected_query': corrected,
                    'was_corrected': True
                }

    return {
        'results': results,
        'suggestion': None,
        'original_query': query,
        'corrected_query': query,
        'was_corrected': False
    }


def suggest_alternatives(query, max_suggestions=3):
    """
    Suggest alternative search queries using LLM.

    Args:
        query: Original query
        max_suggestions: Maximum number of alternatives

    Returns:
        List of alternative queries
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')

        prompt = f"""Given this search query, suggest {max_suggestions} alternative ways to search for the same thing.
Return only the alternative queries, one per line, without numbering or explanation.

Query: {query}

Alternatives:"""

        response = model.generate_content(prompt)
        alternatives = response.text.strip().split('\n')

        # Clean up alternatives
        alternatives = [
            alt.strip().strip('"\'').strip('- ')
            for alt in alternatives
            if alt.strip()
        ][:max_suggestions]

        return alternatives

    except Exception as e:
        print(f"Error suggesting alternatives: {e}")
        return []
