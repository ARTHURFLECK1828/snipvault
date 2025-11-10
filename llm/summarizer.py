"""AI-powered snippet summarization using Gemini."""

import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def generate_snippet_summary(title, code, language, max_length=100):
    """
    Generate AI summary of code snippet using Gemini.

    Args:
        title: Snippet title
        code: Code content
        language: Programming language
        max_length: Maximum summary length in characters

    Returns:
        One-line summary string
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')

        # Limit code length for API efficiency
        code_sample = code[:1000]  # First 1000 chars

        prompt = f"""Provide a concise one-line summary (max {max_length} characters) of what this code does.
Be specific and technical. Focus on functionality, not implementation details.

Title: {title}
Language: {language}
Code:
```{language}
{code_sample}
```

Summary (one line, max {max_length} chars):"""

        response = model.generate_content(prompt)
        summary = response.text.strip()

        # Ensure it's one line and within length
        summary = summary.split('\n')[0][:max_length]

        # Remove quotes if LLM added them
        summary = summary.strip('"\'')

        return summary

    except Exception as e:
        print(f"Error generating summary: {e}")
        return None


def batch_generate_summaries(snippets, progress_callback=None):
    """
    Generate summaries for multiple snippets in batch.

    Args:
        snippets: List of snippet dictionaries
        progress_callback: Optional function to call with progress

    Returns:
        Dict mapping snippet_id to summary
    """
    summaries = {}

    for i, snippet in enumerate(snippets):
        try:
            summary = generate_snippet_summary(
                snippet['title'],
                snippet['code'],
                snippet['language']
            )

            if summary:
                summaries[snippet['id']] = summary

            if progress_callback:
                progress_callback(i + 1, len(snippets))

        except Exception as e:
            print(f"Error generating summary for snippet {snippet['id']}: {e}")
            continue

    return summaries


def enhance_snippet_with_summary(snippet):
    """
    Add summary to snippet dict if not present.

    Args:
        snippet: Snippet dictionary

    Returns:
        Snippet with summary added
    """
    if not snippet.get('summary'):
        summary = generate_snippet_summary(
            snippet['title'],
            snippet['code'],
            snippet['language']
        )
        snippet['summary'] = summary

    return snippet
