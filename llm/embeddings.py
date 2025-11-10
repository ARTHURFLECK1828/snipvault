"""Embedding generation using Google Gemini API."""

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)


def generate_embedding(text):
    """
    Generate embedding for given text using Gemini text-embedding-004.

    Args:
        text: Text to embed (snippet title + code + tags)

    Returns:
        List of floats representing the embedding vector (768 dimensions)
    """
    # Check for empty text
    if not text or not text.strip():
        return None

    try:
        # Use Gemini's embedding model
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )

        # Handle both dict and object responses
        if isinstance(result, dict):
            return result.get('embedding')
        else:
            return result.embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def generate_query_embedding(query):
    """
    Generate embedding for search query using Gemini text-embedding-004.

    Args:
        query: Search query text

    Returns:
        List of floats representing the embedding vector (768 dimensions)
    """
    try:
        # Use Gemini's embedding model with query task type
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query"
        )

        # Handle both dict and object responses
        if isinstance(result, dict):
            return result.get('embedding')
        else:
            return result.embedding
    except Exception as e:
        print(f"Error generating query embedding: {e}")
        return None


def prepare_snippet_text(title, code, tags=None):
    """
    Prepare snippet text for embedding by combining title, code, and tags.

    Args:
        title: Snippet title
        code: Code content
        tags: List of tags (optional)

    Returns:
        Combined text string
    """
    parts = [f"Title: {title}", f"Code: {code}"]

    if tags:
        tags_str = ", ".join(tags)
        parts.append(f"Tags: {tags_str}")

    return "\n".join(parts)


def generate_batch_embeddings(texts):
    """
    Generate embeddings for a batch of texts.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors (same length as input, None for failures)
    """
    embeddings = []

    for text in texts:
        embedding = generate_embedding(text)
        embeddings.append(embedding)

    return embeddings
