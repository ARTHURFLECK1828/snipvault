"""Setup script for SnipVault."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [
            line.strip() for line in f
            if line.strip() and not line.startswith('#')
        ]
else:
    requirements = []

setup(
    name="snipvault",
    version="1.0.1",
    author="SnipVault Team",
    author_email="catcharavind18@gmail.com",
    description="LLM-Powered Code Snippet Manager with vector search",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ARTHURFLECK1828/snipvault",
    project_urls={
        "Bug Tracker": "https://github.com/ARTHURFLECK1828/snipvault/issues",
        "Documentation": "https://github.com/ARTHURFLECK1828/snipvault#readme",
        "Source Code": "https://github.com/ARTHURFLECK1828/snipvault",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "ruff>=0.1.8",
            "black>=23.12.1",
            "mypy>=1.7.1",
        ],
        "local": [
            "sentence-transformers>=2.2.2",
            "torch>=2.0.0",
        ],
        "openai": [
            "openai>=1.3.0",
        ],
        "github": [
            "PyGithub>=2.1.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "snipvault=snipvault.__main__:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.sql"],
    },
    keywords=[
        "code-snippets",
        "llm",
        "vector-search",
        "cli",
        "gemini",
        "postgresql",
        "pinecone",
        "embeddings",
        "semantic-search",
    ],
    license="MIT",
)
