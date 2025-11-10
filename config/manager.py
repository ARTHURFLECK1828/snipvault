"""
Configuration management for SnipVault.

Supports multiple profiles, YAML configuration files, and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from utils.exceptions import MissingConfigError, InvalidConfigError, ConfigurationError


class ConfigManager:
    """Manages SnipVault configuration with multiple profiles."""

    DEFAULT_CONFIG = {
        'database': {
            'postgres': {
                'host': 'localhost',
                'port': 5432,
                'database': 'snipvault',
                'user': 'postgres',
                'password': '',
                'pool_size': 10,
                'max_overflow': 20
            },
            'sqlite': {
                'enabled': False,
                'path': '~/.snipvault/snipvault.db'
            }
        },
        'vector_db': {
            'provider': 'pinecone',  # pinecone | local
            'pinecone': {
                'api_key': '',
                'environment': '',
                'index_name': 'snipvault'
            }
        },
        'embeddings': {
            'provider': 'gemini',  # gemini | openai | local
            'dimension': 768,
            'gemini': {
                'api_key': '',
                'model': 'models/text-embedding-004'
            },
            'openai': {
                'api_key': '',
                'model': 'text-embedding-3-small'
            },
            'local': {
                'model': 'sentence-transformers/all-MiniLM-L6-v2',
                'cache_dir': '~/.snipvault/models'
            }
        },
        'llm': {
            'provider': 'gemini',  # gemini | openai
            'gemini': {
                'api_key': '',
                'model': 'gemini-2.5-flash'
            },
            'openai': {
                'api_key': '',
                'model': 'gpt-4o-mini'
            }
        },
        'search': {
            'default_top_k': 5,
            'hybrid_enabled': True,
            'fuzzy_enabled': True,
            'vector_weight': 0.6,
            'keyword_weight': 0.4
        },
        'cache': {
            'enabled': True,
            'directory': '~/.snipvault/cache',
            'embedding_ttl': 86400,  # 24 hours
            'max_size_mb': 500
        },
        'logging': {
            'level': 'INFO',
            'file': True,
            'console': True,
            'max_file_size_mb': 10,
            'backup_count': 5
        },
        'github': {
            'api_token': '',
            'default_visibility': 'private'
        },
        'performance': {
            'async_enabled': False,
            'batch_size': 10,
            'concurrent_requests': 5
        }
    }

    def __init__(self, profile: str = 'default', config_file: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            profile: Configuration profile to use
            config_file: Path to custom config file
        """
        self.profile = profile
        self.config_dir = Path.home() / '.snipvault'
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = config_file or (self.config_dir / 'config.yaml')
        self.config: Dict[str, Any] = {}

        self._load_config()

    def _load_config(self):
        """Load configuration from file and environment variables."""
        # Load .env file
        load_dotenv()

        # Start with default config
        self.config = self.DEFAULT_CONFIG.copy()

        # Load from YAML if exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    file_config = yaml.safe_load(f) or {}

                # Get profile-specific config
                if 'profiles' in file_config and self.profile in file_config['profiles']:
                    profile_config = file_config['profiles'][self.profile]
                    self._deep_merge(self.config, profile_config)
                # Or use default config
                elif 'default' in file_config:
                    self._deep_merge(self.config, file_config['default'])

            except Exception as e:
                raise ConfigurationError(f"Failed to load config file: {e}")

        # Override with environment variables
        self._load_from_env()

    def _deep_merge(self, base: Dict, override: Dict):
        """
        Deep merge two dictionaries.

        Args:
            base: Base dictionary to merge into
            override: Dictionary with override values
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _load_from_env(self):
        """Load configuration from environment variables."""
        # PostgreSQL
        if os.getenv('POSTGRES_HOST'):
            self.config['database']['postgres']['host'] = os.getenv('POSTGRES_HOST')
        if os.getenv('POSTGRES_PORT'):
            self.config['database']['postgres']['port'] = int(os.getenv('POSTGRES_PORT'))
        if os.getenv('POSTGRES_DB'):
            self.config['database']['postgres']['database'] = os.getenv('POSTGRES_DB')
        if os.getenv('POSTGRES_USER'):
            self.config['database']['postgres']['user'] = os.getenv('POSTGRES_USER')
        if os.getenv('POSTGRES_PASSWORD'):
            self.config['database']['postgres']['password'] = os.getenv('POSTGRES_PASSWORD')

        # Pinecone
        if os.getenv('PINECONE_API_KEY'):
            self.config['vector_db']['pinecone']['api_key'] = os.getenv('PINECONE_API_KEY')
        if os.getenv('PINECONE_ENVIRONMENT'):
            self.config['vector_db']['pinecone']['environment'] = os.getenv('PINECONE_ENVIRONMENT')

        # Gemini
        if os.getenv('GEMINI_API_KEY'):
            self.config['embeddings']['gemini']['api_key'] = os.getenv('GEMINI_API_KEY')
            self.config['llm']['gemini']['api_key'] = os.getenv('GEMINI_API_KEY')

        # OpenAI
        if os.getenv('OPENAI_API_KEY'):
            self.config['embeddings']['openai']['api_key'] = os.getenv('OPENAI_API_KEY')
            self.config['llm']['openai']['api_key'] = os.getenv('OPENAI_API_KEY')

        # GitHub
        if os.getenv('GITHUB_TOKEN'):
            self.config['github']['api_token'] = os.getenv('GITHUB_TOKEN')

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path.

        Args:
            key_path: Dot-separated path (e.g., 'database.postgres.host')
            default: Default value if key not found

        Returns:
            Configuration value

        Example:
            config.get('database.postgres.host')
            config.get('search.default_top_k', 10)
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def require(self, key_path: str) -> Any:
        """
        Get required configuration value, raise error if missing.

        Args:
            key_path: Dot-separated path

        Returns:
            Configuration value

        Raises:
            MissingConfigError: If configuration key is missing
        """
        value = self.get(key_path)
        if value is None or value == '':
            raise MissingConfigError(key_path)
        return value

    def set(self, key_path: str, value: Any):
        """
        Set configuration value by dot-separated path.

        Args:
            key_path: Dot-separated path
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def save(self):
        """Save current configuration to file."""
        try:
            config_data = {
                'profiles': {
                    self.profile: self.config
                }
            }

            # If file exists, preserve other profiles
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    existing = yaml.safe_load(f) or {}

                if 'profiles' in existing:
                    for profile_name, profile_config in existing['profiles'].items():
                        if profile_name != self.profile:
                            config_data['profiles'][profile_name] = profile_config

            with open(self.config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)

        except Exception as e:
            raise ConfigurationError(f"Failed to save config file: {e}")

    def create_profile(self, profile_name: str, base_profile: str = 'default'):
        """
        Create a new configuration profile.

        Args:
            profile_name: Name of the new profile
            base_profile: Profile to copy from
        """
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                existing = yaml.safe_load(f) or {}
        else:
            existing = {'profiles': {}}

        if 'profiles' not in existing:
            existing['profiles'] = {}

        # Copy base profile or use default config
        if base_profile in existing.get('profiles', {}):
            existing['profiles'][profile_name] = existing['profiles'][base_profile].copy()
        else:
            existing['profiles'][profile_name] = self.DEFAULT_CONFIG.copy()

        with open(self.config_file, 'w') as f:
            yaml.dump(existing, f, default_flow_style=False, indent=2)

    def list_profiles(self) -> list:
        """
        List all available configuration profiles.

        Returns:
            List of profile names
        """
        if not self.config_file.exists():
            return ['default']

        with open(self.config_file, 'r') as f:
            config = yaml.safe_load(f) or {}

        return list(config.get('profiles', {}).keys())


# Global config instance
_config_instance: Optional[ConfigManager] = None


def get_config(profile: str = 'default') -> ConfigManager:
    """
    Get global configuration instance.

    Args:
        profile: Configuration profile to use

    Returns:
        ConfigManager instance
    """
    global _config_instance

    if _config_instance is None or _config_instance.profile != profile:
        _config_instance = ConfigManager(profile=profile)

    return _config_instance


def reload_config(profile: str = 'default'):
    """
    Reload configuration from file.

    Args:
        profile: Configuration profile to use
    """
    global _config_instance
    _config_instance = ConfigManager(profile=profile)
