"""
Custom exceptions for SnipVault.

Provides specific exception types for better error handling
and more informative error messages.
"""


class SnipVaultError(Exception):
    """Base exception for all SnipVault errors."""

    def __init__(self, message: str, details: str = None):
        """
        Initialize exception.

        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format the exception message."""
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


class DatabaseError(SnipVaultError):
    """Database-related errors."""
    pass


class ConnectionError(DatabaseError):
    """Database connection errors."""
    pass


class QueryError(DatabaseError):
    """Database query execution errors."""
    pass


class MigrationError(DatabaseError):
    """Database migration errors."""
    pass


class VectorDatabaseError(SnipVaultError):
    """Vector database (Pinecone) errors."""
    pass


class EmbeddingError(SnipVaultError):
    """Embedding generation errors."""
    pass


class APIError(SnipVaultError):
    """External API call errors."""
    pass


class GeminiAPIError(APIError):
    """Google Gemini API errors."""
    pass


class PineconeAPIError(APIError):
    """Pinecone API errors."""
    pass


class GitHubAPIError(APIError):
    """GitHub API errors."""
    pass


class SnippetNotFoundError(SnipVaultError):
    """Snippet not found in database."""

    def __init__(self, snippet_id: int):
        """
        Initialize exception.

        Args:
            snippet_id: ID of the snippet that wasn't found
        """
        super().__init__(
            f"Snippet with ID {snippet_id} not found",
            details="The requested snippet does not exist in the database"
        )
        self.snippet_id = snippet_id


class DuplicateSnippetError(SnipVaultError):
    """Duplicate snippet detected."""

    def __init__(self, existing_id: int):
        """
        Initialize exception.

        Args:
            existing_id: ID of the existing snippet
        """
        super().__init__(
            f"Duplicate snippet detected (existing ID: {existing_id})",
            details="A snippet with identical code already exists"
        )
        self.existing_id = existing_id


class ValidationError(SnipVaultError):
    """Input validation errors."""

    def __init__(self, field: str, message: str):
        """
        Initialize exception.

        Args:
            field: Name of the invalid field
            message: Validation error message
        """
        super().__init__(
            f"Validation error for '{field}': {message}"
        )
        self.field = field


class ConfigurationError(SnipVaultError):
    """Configuration-related errors."""
    pass


class MissingConfigError(ConfigurationError):
    """Missing required configuration."""

    def __init__(self, config_key: str):
        """
        Initialize exception.

        Args:
            config_key: Name of the missing configuration key
        """
        super().__init__(
            f"Missing required configuration: {config_key}",
            details="Please check your .env file or config.yaml"
        )
        self.config_key = config_key


class InvalidConfigError(ConfigurationError):
    """Invalid configuration value."""

    def __init__(self, config_key: str, value: str, expected: str):
        """
        Initialize exception.

        Args:
            config_key: Name of the configuration key
            value: Invalid value
            expected: Expected value format
        """
        super().__init__(
            f"Invalid configuration for '{config_key}': {value}",
            details=f"Expected: {expected}"
        )
        self.config_key = config_key
        self.value = value


class FileOperationError(SnipVaultError):
    """File operation errors."""
    pass


class FileNotFoundError(FileOperationError):
    """File not found error."""

    def __init__(self, file_path: str):
        """
        Initialize exception.

        Args:
            file_path: Path to the file that wasn't found
        """
        super().__init__(
            f"File not found: {file_path}"
        )
        self.file_path = file_path


class FileParseError(FileOperationError):
    """File parsing error."""

    def __init__(self, file_path: str, reason: str):
        """
        Initialize exception.

        Args:
            file_path: Path to the file that couldn't be parsed
            reason: Reason for parse failure
        """
        super().__init__(
            f"Failed to parse file: {file_path}",
            details=reason
        )
        self.file_path = file_path


class SearchError(SnipVaultError):
    """Search-related errors."""
    pass


class EmptyResultsError(SearchError):
    """No search results found."""

    def __init__(self, query: str):
        """
        Initialize exception.

        Args:
            query: Search query that returned no results
        """
        super().__init__(
            f"No results found for query: '{query}'",
            details="Try using different keywords or check for typos"
        )
        self.query = query


class ImportError(SnipVaultError):
    """Import operation errors."""
    pass


class ExportError(SnipVaultError):
    """Export operation errors."""
    pass


class CacheError(SnipVaultError):
    """Caching-related errors."""
    pass


class RateLimitError(APIError):
    """API rate limit exceeded."""

    def __init__(self, api_name: str, retry_after: int = None):
        """
        Initialize exception.

        Args:
            api_name: Name of the API that hit rate limit
            retry_after: Seconds to wait before retrying
        """
        message = f"{api_name} API rate limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after} seconds"

        super().__init__(message)
        self.api_name = api_name
        self.retry_after = retry_after
