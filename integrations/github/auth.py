"""
GitHub API authentication and client management.

Handles authentication using personal access tokens and
provides a configured GitHub client.
"""

from typing import Optional
from pathlib import Path
from utils.logger import get_logger
from utils.exceptions import GitHubAPIError, ConfigurationError
from config import get_config

logger = get_logger(__name__)


class GitHubAuthManager:
    """Manage GitHub API authentication."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub auth manager.

        Args:
            token: GitHub personal access token
        """
        self.token = token or self._get_token_from_config()

        if not self.token:
            raise ConfigurationError(
                "GitHub token not configured. "
                "Set GITHUB_TOKEN environment variable or add to config.yaml"
            )

        self.client = None
        self._initialize_client()

    def _get_token_from_config(self) -> Optional[str]:
        """
        Get GitHub token from configuration.

        Returns:
            GitHub token or None
        """
        try:
            config = get_config()
            return config.get('github.api_token')
        except Exception:
            return None

    def _initialize_client(self):
        """Initialize GitHub client."""
        try:
            from github import Github, Auth

            auth = Auth.Token(self.token)
            self.client = Github(auth=auth)

            # Test authentication
            user = self.client.get_user()
            logger.info(f"Authenticated as GitHub user: {user.login}")

        except ImportError:
            raise GitHubAPIError(
                "PyGithub not installed. "
                "Install with: pip install PyGithub"
            )
        except Exception as e:
            logger.error(f"GitHub authentication failed: {e}")
            raise GitHubAPIError(f"GitHub authentication failed: {e}")

    def get_client(self):
        """
        Get authenticated GitHub client.

        Returns:
            GitHub client instance
        """
        return self.client

    def test_connection(self) -> bool:
        """
        Test GitHub API connection.

        Returns:
            True if connection successful
        """
        try:
            user = self.client.get_user()
            logger.info(f"Connection test successful: {user.login}")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_rate_limit(self) -> dict:
        """
        Get current rate limit status.

        Returns:
            Dictionary with rate limit info
        """
        try:
            rate_limit = self.client.get_rate_limit()

            return {
                'core': {
                    'limit': rate_limit.core.limit,
                    'remaining': rate_limit.core.remaining,
                    'reset': rate_limit.core.reset.isoformat()
                },
                'search': {
                    'limit': rate_limit.search.limit,
                    'remaining': rate_limit.search.remaining,
                    'reset': rate_limit.search.reset.isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit: {e}")
            return {}

    def check_rate_limit_warning(self):
        """Check and warn if rate limit is low."""
        try:
            rate_limit = self.get_rate_limit()

            core_remaining = rate_limit.get('core', {}).get('remaining', 0)

            if core_remaining < 100:
                logger.warning(
                    f"⚠ GitHub API rate limit low: {core_remaining} requests remaining"
                )

        except Exception:
            pass


# Global auth manager instance
_auth_manager: Optional[GitHubAuthManager] = None


def get_github_client():
    """
    Get global GitHub client instance.

    Returns:
        Authenticated GitHub client
    """
    global _auth_manager

    if _auth_manager is None:
        _auth_manager = GitHubAuthManager()

    return _auth_manager.get_client()


def get_auth_manager() -> GitHubAuthManager:
    """
    Get global auth manager instance.

    Returns:
        GitHubAuthManager instance
    """
    global _auth_manager

    if _auth_manager is None:
        _auth_manager = GitHubAuthManager()

    return _auth_manager
