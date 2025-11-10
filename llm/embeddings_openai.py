"""
OpenAI embeddings integration.

Provides embedding generation using OpenAI's embedding models.
"""

from typing import List, Optional
import time
from utils.logger import get_logger
from utils.exceptions import EmbeddingError, RateLimitError
from utils.api_tracker import track_api_call

logger = get_logger(__name__)


class OpenAIEmbeddingGenerator:
    """Generate embeddings using OpenAI API."""

    def __init__(
        self,
        api_key: str,
        model: str = 'text-embedding-3-small'
    ):
        """
        Initialize OpenAI embedding generator.

        Args:
            api_key: OpenAI API key
            model: Model name (text-embedding-3-small or text-embedding-3-large)
        """
        self.api_key = api_key
        self.model = model

        self.client = None
        self.dimension = 1536  # Default for text-embedding-3-small

        self._initialize_client()

    def _initialize_client(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=self.api_key)

            # Set dimension based on model
            if self.model == 'text-embedding-3-small':
                self.dimension = 1536
            elif self.model == 'text-embedding-3-large':
                self.dimension = 3072

            logger.info(f"OpenAI client initialized with model: {self.model}")

        except ImportError:
            raise EmbeddingError(
                "openai package not installed. "
                "Install with: pip install openai"
            )
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise EmbeddingError(f"Failed to initialize OpenAI client: {e}")

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text.

        Args:
            text: Input text

        Returns:
            Embedding vector or None on error
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None

        try:
            start_time = time.time()

            # Generate embedding
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )

            embedding = response.data[0].embedding
            duration_ms = (time.time() - start_time) * 1000

            # Track API call
            tokens = response.usage.total_tokens
            track_api_call(
                service='openai',
                operation='embed',
                tokens=tokens,
                items=1,
                duration_ms=duration_ms,
                status='success',
                model=self.model
            )

            logger.debug(
                f"Generated OpenAI embedding in {duration_ms:.2f}ms "
                f"({tokens} tokens)"
            )

            return embedding

        except Exception as e:
            error_msg = str(e)

            # Handle rate limiting
            if 'rate_limit' in error_msg.lower():
                logger.error("OpenAI rate limit exceeded")
                track_api_call(
                    service='openai',
                    operation='embed',
                    tokens=len(text),
                    status='error',
                    model=self.model
                )
                raise RateLimitError('openai', retry_after=60)

            logger.error(f"Error generating OpenAI embedding: {e}")
            track_api_call(
                service='openai',
                operation='embed',
                tokens=len(text),
                status='error',
                model=self.model
            )
            return None

    def generate_batch_embeddings(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of input texts
            batch_size: Batch size (max 2048 for OpenAI)

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        results = []

        # Filter out empty texts
        valid_texts = [t for t in texts if t and t.strip()]

        if not valid_texts:
            return [None] * len(texts)

        try:
            start_time = time.time()

            # Process in batches
            for i in range(0, len(valid_texts), batch_size):
                batch = valid_texts[i:i + batch_size]

                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )

                batch_embeddings = [item.embedding for item in response.data]
                results.extend(batch_embeddings)

                # Track batch
                tokens = response.usage.total_tokens
                track_api_call(
                    service='openai',
                    operation='embed_batch',
                    tokens=tokens,
                    items=len(batch),
                    duration_ms=0,  # Updated below
                    status='success',
                    model=self.model
                )

            duration_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Generated {len(results)} OpenAI embeddings in {duration_ms:.2f}ms "
                f"({duration_ms/len(results):.2f}ms per embedding)"
            )

            # Map embeddings back to original indices
            result_map = {}
            valid_idx = 0
            for i, text in enumerate(texts):
                if text and text.strip():
                    result_map[i] = results[valid_idx]
                    valid_idx += 1
                else:
                    result_map[i] = None

            return [result_map[i] for i in range(len(texts))]

        except Exception as e:
            error_msg = str(e)

            if 'rate_limit' in error_msg.lower():
                logger.error("OpenAI rate limit exceeded")
                raise RateLimitError('openai', retry_after=60)

            logger.error(f"Error generating batch OpenAI embeddings: {e}")
            return [None] * len(texts)

    def get_dimension(self) -> int:
        """
        Get embedding dimension.

        Returns:
            Embedding dimension
        """
        return self.dimension


# Supported OpenAI models
SUPPORTED_MODELS = {
    'text-embedding-3-small': {
        'dimension': 1536,
        'description': 'Small, efficient model (default)',
        'cost_per_1m_tokens': 0.02
    },
    'text-embedding-3-large': {
        'dimension': 3072,
        'description': 'Large, high-quality model',
        'cost_per_1m_tokens': 0.13
    },
    'text-embedding-ada-002': {
        'dimension': 1536,
        'description': 'Legacy model (deprecated)',
        'cost_per_1m_tokens': 0.10
    }
}


def list_supported_models() -> dict:
    """
    List all supported OpenAI models.

    Returns:
        Dictionary of supported models with metadata
    """
    return SUPPORTED_MODELS
