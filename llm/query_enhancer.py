"""Query enhancement using Google Gemini LLM."""

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)


def enhance_query(user_query):
    """
    Enhance user query using Gemini LLM to improve search results.

    The LLM expands the query with related terms, synonyms, and technical
    variations to improve semantic search accuracy.

    Args:
        user_query: Original user search query

    Returns:
        Enhanced query string with expanded terms
    """
    try:
        # Create the prompt for query enhancement
        prompt = f"""You are a code search assistant. Enhance the following search query for better code snippet retrieval.

Task: Expand the query with related programming terms, synonyms, common variations, and related concepts.

Original Query: "{user_query}"

Guidelines:
- Add technical synonyms and related terms
- Include common abbreviations and full forms
- Add related programming concepts
- Keep it concise (max 50 words)
- Focus on programming/code context
- Do not add explanations, just return the enhanced query

Enhanced Query:"""

        # Use Gemini to enhance the query
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)

        enhanced = response.text.strip()

        # Fallback to original query if enhancement fails
        if not enhanced or len(enhanced) < 3:
            return user_query

        return enhanced

    except Exception as e:
        print(f"Warning: Query enhancement failed ({e}), using original query")
        return user_query


def enhance_query_simple(user_query):
    """
    Simple query enhancement without LLM (fallback option).

    Args:
        user_query: Original user search query

    Returns:
        Original query (no enhancement)
    """
    return user_query
