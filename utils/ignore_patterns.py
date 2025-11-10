"""Ignore pattern handling for file filtering."""

import fnmatch
import os
from pathlib import Path
from typing import List, Set


class IgnorePatternMatcher:
    """Handles .gitignore-style pattern matching."""

    def __init__(self, patterns: List[str] = None):
        """
        Initialize with list of ignore patterns.

        Args:
            patterns: List of gitignore-style patterns
        """
        self.patterns = patterns or []
        self._compile_patterns()

    def _compile_patterns(self):
        """Process patterns into usable form."""
        self.include_patterns = []
        self.exclude_patterns = []

        for pattern in self.patterns:
            pattern = pattern.strip()

            # Skip empty lines and comments
            if not pattern or pattern.startswith('#'):
                continue

            # Negation pattern (include)
            if pattern.startswith('!'):
                self.include_patterns.append(pattern[1:])
            else:
                self.exclude_patterns.append(pattern)

    def should_ignore(self, path: str, is_dir: bool = False) -> bool:
        """
        Check if path should be ignored.

        Args:
            path: Path to check
            is_dir: Whether path is a directory

        Returns:
            True if path should be ignored
        """
        # Normalize path
        path = path.replace('\\', '/')

        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if self._matches_pattern(path, pattern, is_dir):
                # Check if explicitly included
                for include_pattern in self.include_patterns:
                    if self._matches_pattern(path, include_pattern, is_dir):
                        return False
                return True

        return False

    def _matches_pattern(self, path: str, pattern: str, is_dir: bool) -> bool:
        """
        Check if path matches a gitignore pattern.

        Args:
            path: Path to check
            pattern: Gitignore pattern
            is_dir: Whether path is a directory

        Returns:
            True if pattern matches
        """
        # Directory-only pattern
        if pattern.endswith('/'):
            if not is_dir:
                return False
            pattern = pattern[:-1]

        # Pattern with slash (matches from root or specific path)
        if '/' in pattern:
            # Absolute pattern
            if pattern.startswith('/'):
                pattern = pattern[1:]
                return fnmatch.fnmatch(path, pattern)
            # Relative pattern
            else:
                return fnmatch.fnmatch(path, f'*/{pattern}') or fnmatch.fnmatch(path, pattern)

        # Simple pattern (matches anywhere in path)
        parts = path.split('/')
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True

        return False

    @classmethod
    def from_file(cls, ignore_file: str):
        """
        Create matcher from .gitignore-style file.

        Args:
            ignore_file: Path to ignore file

        Returns:
            IgnorePatternMatcher instance
        """
        patterns = []

        if os.path.exists(ignore_file):
            with open(ignore_file, 'r') as f:
                patterns = f.readlines()

        return cls(patterns)

    @classmethod
    def from_directory(cls, directory: str):
        """
        Create matcher by looking for .snipignore or .gitignore in directory.

        Args:
            directory: Directory to search

        Returns:
            IgnorePatternMatcher instance
        """
        dir_path = Path(directory)

        # Check for .snipignore first
        snipignore = dir_path / '.snipignore'
        if snipignore.exists():
            return cls.from_file(str(snipignore))

        # Fall back to .gitignore
        gitignore = dir_path / '.gitignore'
        if gitignore.exists():
            return cls.from_file(str(gitignore))

        return cls()


def get_default_ignore_patterns() -> List[str]:
    """Get default ignore patterns for code import."""
    return [
        # Version control
        '.git/',
        '.svn/',
        '.hg/',

        # Dependencies
        'node_modules/',
        'vendor/',
        'bower_components/',

        # Python
        '__pycache__/',
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '.Python',
        'venv/',
        'env/',
        '.venv/',
        'virtualenv/',
        '.pytest_cache/',
        '.mypy_cache/',
        '.tox/',
        '*.egg-info/',

        # Build outputs
        'build/',
        'dist/',
        'target/',
        'bin/',
        'obj/',
        'out/',

        # IDE
        '.idea/',
        '.vscode/',
        '*.swp',
        '*.swo',
        '*~',
        '.DS_Store',

        # Logs
        '*.log',
        'logs/',

        # Databases
        '*.db',
        '*.sqlite',
        '*.sqlite3',

        # Compiled
        '*.so',
        '*.dylib',
        '*.dll',
        '*.exe',

        # Archives
        '*.zip',
        '*.tar.gz',
        '*.rar',

        # Config/env
        '.env',
        '.env.local',
        '*.lock',

        # Documentation builds
        'docs/_build/',
        'site/',

        # Coverage
        'coverage/',
        '.coverage',
        'htmlcov/',
    ]
