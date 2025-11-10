"""
Embedding model factory with dynamic selection and hybrid fallback.

Provides a unified interface for different embedding providers
with automatic fallback from local to cloud.
"""

from typing import List, Optional, Protocol
from enum import Enum
from utils.logger import get_logger
from utils.exceptions import EmbeddingError, ConfigurationError
from config import get_config

logger = get_logger(__name__)


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    GEMINI = "gemini"
    OPENAI = "openai"
    LOCAL = "local"


class EmbeddingGenerator(Protocol):
    """Protocol for embedding generators."""

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for single text."""
        ...

    def generate_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts."""
        ...

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        ...


class EmbeddingFactory:
    """Factory for creating embedding generators."""

    _instances = {}

    @classmethod
    def create_generator(
        cls,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> EmbeddingGenerator:
        """
        Create an embedding generator.

        Args:
            provider: Provider name (gemini, openai, local)
            model: Model name (optional, uses config default)

        Returns:
            EmbeddingGenerator instance

        Raises:
            ConfigurationError: If configuration is invalid
            EmbeddingError: If generator creation fails
        """
        config = get_config()

        # Get provider from config if not specified
        if provider is None:
            provider = config.get('embeddings.provider', 'gemini')

        # Cache key
        cache_key = f"{provider}:{model}" if model else provider

        # Return cached instance if available
        if cache_key in cls._instances:
            return cls._instances[cache_key]

        # Create new instance
        try:
            if provider == EmbeddingProvider.GEMINI:
                generator = cls._create_gemini_generator(config, model)

            elif provider == EmbeddingProvider.OPENAI:
                generator = cls._create_openai_generator(config, model)

            elif provider == EmbeddingProvider.LOCAL:
                generator = cls._create_local_generator(config, model)

            else:
                raise ConfigurationError(
                    f"Unknown embedding provider: {provider}. "
                    f"Supported: {[p.value for p in EmbeddingProvider]}"
                )

            # Cache and return
            cls._instances[cache_key] = generator
            logger.info(f"Created {provider} embedding generator (model: {model or 'default'})")
            return generator

        except Exception as e:
            logger.error(f"Failed to create {provider} embedding generator: {e}")
            raise

    @staticmethod
    def _create_gemini_generator(config, model: Optional[str]):
        """Create Gemini embedding generator."""
        from llm.embeddings import generate_embedding, generate_batch_embeddings

        # Create a wrapper class to match the protocol
        class GeminiGenerator:
            def __init__(self):
                self.dimension = 768

            def generate_embedding(self, text: str) -> Optional[List[float]]:
                return generate_embedding(text)

            def generate_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
                return generate_batch_embeddings(texts)

            def get_dimension(self) -> int:
                return self.dimension

        return GeminiGenerator()

    @staticmethod
    def _create_openai_generator(config, model: Optional[str]):
        """Create OpenAI embedding generator."""
        from llm.embeddings_openai import OpenAIEmbeddingGenerator

        api_key = config.require('embeddings.openai.api_key')
        model_name = model or config.get('embeddings.openai.model', 'text-embedding-3-small')

        return OpenAIEmbeddingGenerator(api_key=api_key, model=model_name)

    @staticmethod
    def _create_local_generator(config, model: Optional[str]):
        """Create local embedding generator."""
        from llm.embeddings_local import LocalEmbeddingGenerator

        model_name = model or config.get(
            'embeddings.local.model',
            'sentence-transformers/all-MiniLM-L6-v2'
        )
        cache_dir = config.get('embeddings.local.cache_dir')

        return LocalEmbeddingGenerator(model_name=model_name, cache_dir=cache_dir)


class HybridEmbeddingGenerator:
    """
    Hybrid embedding generator with automatic fallback.

    Tries local first, falls back to cloud on failure or
    for better quality based on configuration.
    """

    def __init__(
        self,
        primary_provider: str = 'local',
        fallback_provider: str = 'gemini',
        always_use_fallback_for_critical: bool = False
    ):
        """
        Initialize hybrid generator.

        Args:
            primary_provider: Primary provider to try first
            fallback_provider: Fallback provider if primary fails
            always_use_fallback_for_critical: Use fallback for important operations
        """
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        self.always_use_fallback_for_critical = always_use_fallback_for_critical

        self.primary_generator = EmbeddingFactory.create_generator(primary_provider)
        self.fallback_generator = EmbeddingFactory.create_generator(fallback_provider)

        logger.info(
            f"Hybrid embedding generator initialized: "
            f"primary={primary_provider}, fallback={fallback_provider}"
        )

    def generate_embedding(
        self,
        text: str,
        critical: bool = False
    ) -> Optional[List[float]]:
        """
        Generate embedding with fallback.

        Args:
            text: Input text
            critical: If True, use fallback for important operations

        Returns:
            Embedding vector or None
        """
        # Use fallback directly for critical operations
        if critical and self.always_use_fallback_for_critical:
            logger.debug(f"Using {self.fallback_provider} for critical operation")
            return self.fallback_generator.generate_embedding(text)

        # Try primary first
        try:
            embedding = self.primary_generator.generate_embedding(text)

            if embedding is not None:
                logger.debug(f"Generated embedding using {self.primary_provider}")
                return embedding

        except Exception as e:
            logger.warning(f"{self.primary_provider} embedding failed: {e}")

        # Fallback to secondary
        try:
            logger.info(f"Falling back to {self.fallback_provider}")
            embedding = self.fallback_generator.generate_embedding(text)

            if embedding is not None:
                logger.debug(f"Generated embedding using {self.fallback_provider} (fallback)")
                return embedding

        except Exception as e:
            logger.error(f"{self.fallback_provider} embedding also failed: {e}")

        return None

    def generate_batch_embeddings(
        self,
        texts: List[str],
        critical: bool = False
    ) -> List[Optional[List[float]]]:
        """
        Generate batch embeddings with fallback.

        Args:
            texts: List of input texts
            critical: If True, use fallback for important operations

        Returns:
            List of embedding vectors
        """
        # Use fallback directly for critical operations
        if critical and self.always_use_fallback_for_critical:
            logger.debug(f"Using {self.fallback_provider} for critical batch operation")
            return self.fallback_generator.generate_batch_embeddings(texts)

        # Try primary first
        try:
            embeddings = self.primary_generator.generate_batch_embeddings(texts)

            # Check if all succeeded
            if all(e is not None for e in embeddings):
                logger.debug(f"Generated {len(embeddings)} embeddings using {self.primary_provider}")
                return embeddings

            # If some failed, retry failed ones with fallback
            logger.warning(f"Some {self.primary_provider} embeddings failed, retrying with fallback")

        except Exception as e:
            logger.warning(f"{self.primary_provider} batch embedding failed: {e}")
            embeddings = [None] * len(texts)

        # Fallback for failed embeddings
        failed_indices = [i for i, e in enumerate(embeddings) if e is None]

        if failed_indices:
            try:
                logger.info(f"Falling back to {self.fallback_provider} for {len(failed_indices)} embeddings")
                failed_texts = [texts[i] for i in failed_indices]
                fallback_embeddings = self.fallback_generator.generate_batch_embeddings(failed_texts)

                # Merge results
                for i, embedding in zip(failed_indices, fallback_embeddings):
                    embeddings[i] = embedding

            except Exception as e:
                logger.error(f"{self.fallback_provider} fallback also failed: {e}")

        return embeddings

    def get_dimension(self) -> int:
        """
        Get embedding dimension (from primary).

        Returns:
            Embedding dimension
        """
        return self.primary_generator.get_dimension()


# Global hybrid generator instance
_hybrid_generator: Optional[HybridEmbeddingGenerator] = None


def get_embedding_generator(use_hybrid: bool = False) -> EmbeddingGenerator:
    """
    Get embedding generator based on configuration.

    Args:
        use_hybrid: Use hybrid generator with fallback

    Returns:
        EmbeddingGenerator instance
    """
    config = get_config()

    if use_hybrid:
        global _hybrid_generator
        if _hybrid_generator is None:
            primary = config.get('embeddings.provider', 'local')
            fallback = 'gemini' if primary == 'local' else 'local'

            _hybrid_generator = HybridEmbeddingGenerator(
                primary_provider=primary,
                fallback_provider=fallback,
                always_use_fallback_for_critical=True
            )

        return _hybrid_generator

    else:
        provider = config.get('embeddings.provider', 'gemini')
        return EmbeddingFactory.create_generator(provider)
