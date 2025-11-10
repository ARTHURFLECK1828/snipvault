"""File type detection and language inference."""

import os
from pathlib import Path

# Extension to language mapping
EXTENSION_MAP = {
    # Python
    '.py': 'python',
    '.pyw': 'python',
    '.pyi': 'python',

    # JavaScript/TypeScript
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.mjs': 'javascript',
    '.cjs': 'javascript',

    # Web
    '.html': 'html',
    '.htm': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.sass': 'sass',
    '.less': 'less',

    # Java/JVM
    '.java': 'java',
    '.kt': 'kotlin',
    '.kts': 'kotlin',
    '.scala': 'scala',
    '.groovy': 'groovy',

    # C/C++
    '.c': 'c',
    '.h': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.hpp': 'cpp',
    '.hxx': 'cpp',
    '.hh': 'cpp',

    # C#
    '.cs': 'csharp',

    # Go
    '.go': 'go',

    # Rust
    '.rs': 'rust',

    # Ruby
    '.rb': 'ruby',
    '.rake': 'ruby',

    # PHP
    '.php': 'php',
    '.phtml': 'php',

    # Shell
    '.sh': 'bash',
    '.bash': 'bash',
    '.zsh': 'zsh',
    '.fish': 'fish',

    # Swift
    '.swift': 'swift',

    # Objective-C
    '.m': 'objective-c',
    '.mm': 'objective-c',

    # R
    '.r': 'r',
    '.R': 'r',

    # SQL
    '.sql': 'sql',

    # YAML/JSON/Config
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.json': 'json',
    '.toml': 'toml',
    '.ini': 'ini',
    '.conf': 'conf',

    # Markdown
    '.md': 'markdown',
    '.markdown': 'markdown',

    # Other
    '.vue': 'vue',
    '.svelte': 'svelte',
    '.dart': 'dart',
    '.lua': 'lua',
    '.pl': 'perl',
    '.pm': 'perl',
    '.ex': 'elixir',
    '.exs': 'elixir',
    '.erl': 'erlang',
    '.hrl': 'erlang',
    '.clj': 'clojure',
    '.cljs': 'clojure',
    '.vim': 'vim',
    '.el': 'elisp',
}

# Common file names to language mapping
FILENAME_MAP = {
    'Makefile': 'makefile',
    'makefile': 'makefile',
    'Dockerfile': 'docker',
    'Vagrantfile': 'ruby',
    'Gemfile': 'ruby',
    'Rakefile': 'ruby',
    '.bashrc': 'bash',
    '.zshrc': 'zsh',
    '.vimrc': 'vim',
}

# File extensions to skip (binary, media, etc.)
SKIP_EXTENSIONS = {
    # Compiled/Binary
    '.pyc', '.pyo', '.so', '.o', '.a', '.exe', '.dll', '.dylib',
    '.jar', '.class', '.war', '.ear',

    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp',

    # Media
    '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',

    # Archives
    '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',

    # Documents
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',

    # Databases
    '.db', '.sqlite', '.sqlite3',

    # Lock files
    '.lock',

    # Maps
    '.map',
}

# Directories to skip by default
SKIP_DIRECTORIES = {
    'node_modules',
    '__pycache__',
    '.git',
    '.svn',
    '.hg',
    'venv',
    'env',
    '.venv',
    '.env',
    'virtualenv',
    'build',
    'dist',
    'target',
    'bin',
    'obj',
    '.idea',
    '.vscode',
    '.cache',
    'coverage',
    '.pytest_cache',
    '.mypy_cache',
    '.tox',
    'vendor',
    'bower_components',
}


def detect_language(file_path):
    """
    Detect programming language from file path.

    Args:
        file_path: Path to the file

    Returns:
        Language string or 'plaintext' if unknown
    """
    path = Path(file_path)

    # Check filename first
    if path.name in FILENAME_MAP:
        return FILENAME_MAP[path.name]

    # Check extension
    ext = path.suffix.lower()
    if ext in EXTENSION_MAP:
        return EXTENSION_MAP[ext]

    return 'plaintext'


def should_skip_file(file_path):
    """
    Check if file should be skipped based on extension.

    Args:
        file_path: Path to the file

    Returns:
        True if file should be skipped
    """
    path = Path(file_path)
    ext = path.suffix.lower()
    return ext in SKIP_EXTENSIONS


def should_skip_directory(dir_name):
    """
    Check if directory should be skipped.

    Args:
        dir_name: Directory name

    Returns:
        True if directory should be skipped
    """
    return dir_name in SKIP_DIRECTORIES


def is_code_file(file_path):
    """
    Check if file is a code file (not binary, media, document, or data file).

    Args:
        file_path: Path to the file

    Returns:
        True if file is a code/text file
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    # Data file extensions (not considered code)
    DATA_EXTENSIONS = {'.json', '.yaml', '.yml', '.toml', '.xml', '.csv'}

    # Check if it's in our skip list (binary, media, docs)
    if ext in SKIP_EXTENSIONS:
        return False

    # Check if it's a data file (not code)
    if ext in DATA_EXTENSIONS:
        return False

    # Check if it's a known code extension
    if ext in EXTENSION_MAP:
        return True

    # Check if it's a known filename
    if path.name in FILENAME_MAP:
        return True

    # For unknown extensions, default to False for safety
    return False


def is_text_file(file_path):
    """
    Check if file is likely a text file.

    Args:
        file_path: Path to the file

    Returns:
        True if file appears to be text
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Try reading first 512 bytes
            f.read(512)
        return True
    except (UnicodeDecodeError, PermissionError):
        return False


def get_supported_extensions():
    """Get list of all supported file extensions."""
    return list(EXTENSION_MAP.keys())


def get_supported_languages():
    """Get list of all supported languages."""
    return sorted(set(EXTENSION_MAP.values()))
