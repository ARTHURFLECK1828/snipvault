"""
Local embeddings using sentence-transformers.

Provides offline embedding generation without API calls,
using pre-trained models from Hugging Face.
"""

from typing import List, Optional
from pathlib import Path
import time
from utils.logger import get_logger
from utils.exceptions import EmbeddingError
from utils.api_tracker import track_api_call

logger = get_logger(__name__)


class LocalEmbeddingGenerator:
    """Generate embeddings locally using sentence-transformers."""

    def __init__(
        self,
        model_name: str = 'sentence-transformers/all-MiniLM-L6-v2',
        cache_dir: Optional[Path] = None,
        device: str = 'cpu'
    ):
        """
        Initialize local embedding generator.

        Args:
            model_name: Hugging Face model name
            cache_dir: Directory to cache models
            device: Device to run model on ('cpu' or 'cuda')
        """
        self.model_name = model_name
        self.cache_dir = cache_dir or (Path.home() / '.snipvault' / 'models')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.device = device

        self.model = None
        self.dimension = 384  # Default for all-MiniLM-L6-v2

        self._load_model()

    def _load_model(self):
        """Load the sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading local embedding model: {self.model_name}")
            start_time = time.time()

            self.model = SentenceTransformer(
                self.model_name,
                cache_folder=str(self.cache_dir),
                device=self.device
            )

            # Get actual dimension
            self.dimension = self.model.get_sentence_embedding_dimension()

            load_time = (time.time() - start_time) * 1000
            logger.info(
                f"Model loaded successfully in {load_time:.0f}ms "
                f"(dimension: {self.dimension})"
            )

        except ImportError:
            raise EmbeddingError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        except Exception as e:
            logger.error(f"Failed to load local embedding model: {e}")
            raise EmbeddingError(f"Failed to load local embedding model: {e}")

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
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False
            )

            duration_ms = (time.time() - start_time) * 1000

            # Track API call (local, so cost is 0)
            track_api_call(
                service='local',
                operation='embed',
                tokens=len(text),
                items=1,
                duration_ms=duration_ms,
                status='success',
                model=self.model_name
            )

            logger.debug(
                f"Generated local embedding in {duration_ms:.2f}ms "
                f"({len(text)} chars)"
            )

            return embedding.tolist()

        except Exception as e:
            logger.error(f"Error generating local embedding: {e}")
            track_api_call(
                service='local',
                operation='embed',
                tokens=len(text),
                status='error',
                model=self.model_name
            )
            return None

    def generate_batch_embeddings(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of input texts
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            start_time = time.time()

            # Filter out empty texts, keeping track of indices
            valid_texts = []
            valid_indices = []
            for i, text in enumerate(texts):
                if text and text.strip():
                    valid_texts.append(text)
                    valid_indices.append(i)

            if not valid_texts:
                return [None] * len(texts)

            # Generate embeddings in batches
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=len(valid_texts) > 100
            )

            duration_ms = (time.time() - start_time) * 1000
            total_chars = sum(len(t) for t in valid_texts)

            # Track API call
            track_api_call(
                service='local',
                operation='embed_batch',
                tokens=total_chars,
                items=len(valid_texts),
                duration_ms=duration_ms,
                status='success',
                model=self.model_name
            )

            logger.info(
                f"Generated {len(valid_texts)} local embeddings in {duration_ms:.2f}ms "
                f"({duration_ms/len(valid_texts):.2f}ms per embedding)"
            )

            # Map embeddings back to original indices
            results = [None] * len(texts)
            for i, embedding in zip(valid_indices, embeddings):
                results[i] = embedding.tolist()

            return results

        except Exception as e:
            logger.error(f"Error generating batch local embeddings: {e}")
            return [None] * len(texts)

    def get_dimension(self) -> int:
        """
        Get embedding dimension.

        Returns:
            Embedding dimension
        """
        return self.dimension


# Supported models with their dimensions
SUPPORTED_MODELS = {
    'sentence-transformers/all-MiniLM-L6-v2': {
        'dimension': 384,
        'description': 'Fast, lightweight model (default)',
        'size_mb': 80
    },
    'sentence-transformers/all-mpnet-base-v2': {
        'dimension': 768,
        'description': 'High quality, general purpose',
        'size_mb': 420
    },
    'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2': {
        'dimension': 384,
        'description': 'Multilingual support, 50+ languages',
        'size_mb': 470
    },
    'BAAI/bge-small-en-v1.5': {
        'dimension': 384,
        'description': 'High performance, small size',
        'size_mb': 130
    },
    'BAAI/bge-base-en-v1.5': {
        'dimension': 768,
        'description': 'High performance, balanced',
        'size_mb': 440
    }
}


def list_supported_models() -> dict:
    """
    List all supported local models.

    Returns:
        Dictionary of supported models with metadata
    """
    return SUPPORTED_MODELS
