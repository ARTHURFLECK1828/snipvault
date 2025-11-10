"""Unit tests for file type detection module."""

import pytest
from pathlib import Path
from utils.file_detector import detect_language, is_code_file, EXTENSION_MAP


class TestFileDetector:
    """Test file type detection functions."""

    def test_detect_language_python(self):
        """Test Python file detection."""
        assert detect_language("test.py") == "python"
        assert detect_language("/path/to/script.py") == "python"

    def test_detect_language_javascript(self):
        """Test JavaScript file detection."""
        assert detect_language("app.js") == "javascript"
        assert detect_language("component.jsx") == "javascript"

    def test_detect_language_typescript(self):
        """Test TypeScript file detection."""
        assert detect_language("app.ts") == "typescript"
        assert detect_language("component.tsx") == "typescript"

    def test_detect_language_by_filename(self):
        """Test detection by specific filename."""
        assert detect_language("Dockerfile") == "docker"
        assert detect_language("Makefile") == "makefile"
        assert detect_language(".bashrc") == "bash"

    def test_detect_language_case_insensitive(self):
        """Test case-insensitive detection."""
        assert detect_language("TEST.PY") == "python"
        assert detect_language("APP.JS") == "javascript"

    def test_detect_language_unknown(self):
        """Test unknown file type."""
        assert detect_language("file.unknown") == "plaintext"
        assert detect_language("no_extension") == "plaintext"

    def test_detect_language_multiple_extensions(self):
        """Test files with multiple extensions."""
        assert detect_language("file.spec.ts") == "typescript"
        assert detect_language("component.test.js") == "javascript"

    def test_is_code_file_valid(self):
        """Test valid code file detection."""
        assert is_code_file("script.py") is True
        assert is_code_file("app.js") is True
        assert is_code_file("style.css") is True

    def test_is_code_file_invalid(self):
        """Test invalid code file detection."""
        assert is_code_file("document.pdf") is False
        assert is_code_file("image.png") is False
        assert is_code_file("data.json") is False  # Depends on configuration

    def test_detect_language_common_languages(self):
        """Test detection for common programming languages."""
        test_cases = {
            "script.py": "python",
            "app.js": "javascript",
            "Main.java": "java",
            "main.cpp": "cpp",
            "program.c": "c",
            "app.go": "go",
            "lib.rs": "rust",
            "script.rb": "ruby",
            "app.php": "php",
            "page.html": "html",
            "style.css": "css",
            "data.json": "json",
            "config.yaml": "yaml",
            "script.sh": "bash",
            "query.sql": "sql",
        }

        for filename, expected_lang in test_cases.items():
            assert detect_language(filename) == expected_lang, \
                f"Failed for {filename}: expected {expected_lang}"

    def test_extension_map_completeness(self):
        """Test that extension map contains common languages."""
        common_extensions = [
            '.py', '.js', '.ts', '.java', '.cpp', '.c',
            '.go', '.rs', '.rb', '.php', '.html', '.css'
        ]

        for ext in common_extensions:
            assert ext in EXTENSION_MAP, f"Missing extension: {ext}"
