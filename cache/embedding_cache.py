"""
Local embedding cache to reduce API calls.

Provides file-based caching with TTL, LRU eviction, and size limits.
"""

import json
import hashlib
import pickle
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from utils.logger import get_logger
from utils.exceptions import CacheError

logger = get_logger(__name__)


class EmbeddingCache:
    """File-based cache for embeddings with TTL and size limits."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl_seconds: int = 86400,  # 24 hours
        max_size_mb: int = 500
    ):
        """
        Initialize embedding cache.

        Args:
            cache_dir: Directory for cache files
            ttl_seconds: Time-to-live for cached embeddings
            max_size_mb: Maximum cache size in megabytes
        """
        self.cache_dir = cache_dir or (Path.home() / '.snipvault' / 'cache' / 'embeddings')
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.ttl = timedelta(seconds=ttl_seconds)
        self.max_size_bytes = max_size_mb * 1024 * 1024

        self.metadata_file = self.cache_dir / 'metadata.json'
        self.metadata = self._load_metadata()

        logger.debug(f"Embedding cache initialized at {self.cache_dir}")

    def _load_metadata(self) -> Dict[str, Any]:
        """
        Load cache metadata.

        Returns:
            Metadata dictionary
        """
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")
                return {'entries': {}, 'total_size': 0}
        return {'entries': {}, 'total_size': 0}

    def _save_metadata(self):
        """Save cache metadata to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")

    def _get_cache_key(self, text: str, model: str = 'default') -> str:
        """
        Generate cache key for text.

        Args:
            text: Input text
            model: Model name

        Returns:
            Cache key (hash)
        """
        key_str = f"{model}:{text}"
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """
        Get cache file path for key.

        Args:
            cache_key: Cache key

        Returns:
            Path to cache file
        """
        return self.cache_dir / f"{cache_key}.pkl"

    def get(self, text: str, model: str = 'default') -> Optional[List[float]]:
        """
        Get embedding from cache.

        Args:
            text: Input text
            model: Model name

        Returns:
            Cached embedding vector or None if not found/expired
        """
        cache_key = self._get_cache_key(text, model)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            logger.debug(f"Cache miss for key {cache_key[:8]}...")
            return None

        # Check if entry exists in metadata
        if cache_key not in self.metadata['entries']:
            logger.debug(f"Cache entry {cache_key[:8]}... not in metadata")
            return None

        entry = self.metadata['entries'][cache_key]

        # Check TTL
        cached_time = datetime.fromisoformat(entry['timestamp'])
        if datetime.now() - cached_time > self.ttl:
            logger.debug(f"Cache entry {cache_key[:8]}... expired")
            self._remove_entry(cache_key)
            return None

        # Load embedding
        try:
            with open(cache_path, 'rb') as f:
                embedding = pickle.load(f)

            # Update access time
            entry['last_accessed'] = datetime.now().isoformat()
            entry['access_count'] = entry.get('access_count', 0) + 1
            self._save_metadata()

            logger.debug(f"Cache hit for key {cache_key[:8]}...")
            return embedding

        except Exception as e:
            logger.error(f"Failed to load cached embedding: {e}")
            self._remove_entry(cache_key)
            return None

    def set(self, text: str, embedding: List[float], model: str = 'default'):
        """
        Store embedding in cache.

        Args:
            text: Input text
            embedding: Embedding vector
            model: Model name
        """
        cache_key = self._get_cache_key(text, model)
        cache_path = self._get_cache_path(cache_key)

        try:
            # Check cache size limit
            if self.metadata['total_size'] >= self.max_size_bytes:
                logger.info("Cache size limit reached, evicting old entries")
                self._evict_lru()

            # Save embedding
            with open(cache_path, 'wb') as f:
                pickle.dump(embedding, f)

            file_size = cache_path.stat().st_size

            # Update metadata
            self.metadata['entries'][cache_key] = {
                'timestamp': datetime.now().isoformat(),
                'last_accessed': datetime.now().isoformat(),
                'access_count': 0,
                'size': file_size,
                'model': model,
                'text_preview': text[:100]
            }

            self.metadata['total_size'] += file_size
            self._save_metadata()

            logger.debug(f"Cached embedding for key {cache_key[:8]}... ({file_size} bytes)")

        except Exception as e:
            logger.error(f"Failed to cache embedding: {e}")
            raise CacheError(f"Failed to cache embedding: {e}")

    def _remove_entry(self, cache_key: str):
        """
        Remove cache entry.

        Args:
            cache_key: Cache key to remove
        """
        cache_path = self._get_cache_path(cache_key)

        if cache_path.exists():
            try:
                cache_path.unlink()
            except Exception as e:
                logger.error(f"Failed to remove cache file: {e}")

        if cache_key in self.metadata['entries']:
            entry_size = self.metadata['entries'][cache_key].get('size', 0)
            self.metadata['total_size'] -= entry_size
            del self.metadata['entries'][cache_key]
            self._save_metadata()

    def _evict_lru(self, target_size_ratio: float = 0.8):
        """
        Evict least recently used entries to free space.

        Args:
            target_size_ratio: Target size as ratio of max size (default: 80%)
        """
        target_size = int(self.max_size_bytes * target_size_ratio)

        # Sort entries by last access time
        entries_by_access = sorted(
            self.metadata['entries'].items(),
            key=lambda x: datetime.fromisoformat(x[1]['last_accessed'])
        )

        # Remove oldest entries until below target
        removed_count = 0
        for cache_key, entry in entries_by_access:
            if self.metadata['total_size'] <= target_size:
                break

            self._remove_entry(cache_key)
            removed_count += 1

        logger.info(f"Evicted {removed_count} cache entries (LRU)")

    def clear_expired(self):
        """Remove all expired cache entries."""
        expired_keys = []

        for cache_key, entry in self.metadata['entries'].items():
            cached_time = datetime.fromisoformat(entry['timestamp'])
            if datetime.now() - cached_time > self.ttl:
                expired_keys.append(cache_key)

        for cache_key in expired_keys:
            self._remove_entry(cache_key)

        if expired_keys:
            logger.info(f"Removed {len(expired_keys)} expired cache entries")

    def clear_all(self):
        """Clear all cache entries."""
        try:
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            self.metadata = {'entries': {}, 'total_size': 0}
            self._save_metadata()

            logger.info("Cache cleared")

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise CacheError(f"Failed to clear cache: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_entries = len(self.metadata['entries'])
        total_size_mb = self.metadata['total_size'] / (1024 * 1024)
        max_size_mb = self.max_size_bytes / (1024 * 1024)
        usage_percent = (self.metadata['total_size'] / self.max_size_bytes) * 100

        # Count by model
        models = {}
        for entry in self.metadata['entries'].values():
            model = entry.get('model', 'default')
            models[model] = models.get(model, 0) + 1

        # Calculate hit rate (would need to track misses)
        total_accesses = sum(
            entry.get('access_count', 0)
            for entry in self.metadata['entries'].values()
        )

        return {
            'total_entries': total_entries,
            'total_size_mb': round(total_size_mb, 2),
            'max_size_mb': max_size_mb,
            'usage_percent': round(usage_percent, 2),
            'models': models,
            'total_accesses': total_accesses,
            'cache_dir': str(self.cache_dir),
            'ttl_hours': self.ttl.total_seconds() / 3600
        }


# Global cache instance
_cache_instance: Optional[EmbeddingCache] = None


def get_embedding_cache() -> EmbeddingCache:
    """
    Get global embedding cache instance.

    Returns:
        EmbeddingCache instance
    """
    global _cache_instance

    if _cache_instance is None:
        from config import get_config

        config = get_config()
        cache_enabled = config.get('cache.enabled', True)

        if cache_enabled:
            cache_dir = Path(config.get('cache.directory', '~/.snipvault/cache')).expanduser()
            ttl = config.get('cache.embedding_ttl', 86400)
            max_size_mb = config.get('cache.max_size_mb', 500)

            _cache_instance = EmbeddingCache(
                cache_dir=cache_dir,
                ttl_seconds=ttl,
                max_size_mb=max_size_mb
            )
        else:
            # Disabled cache returns None for all gets
            _cache_instance = None

    return _cache_instance
