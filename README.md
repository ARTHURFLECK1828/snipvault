# SnipVault
**Because grep isn't enough anymore**

A code snippet manager that actually understands what you're looking for. Search your snippets using natural language, not exact keyword matches.

Built with PostgreSQL for storage, Pinecone for vector search, and Google Gemini/OpenAI for embeddings and query understanding.

## What it does

You know that moment when you remember writing some useful code but can't find it? SnipVault fixes that.

Instead of searching for exact keywords, you can search like: *"that react hook that stores data in localStorage"* and it'll find your useLocalStorage hook even if you never used those exact words in the snippet.

The search combines semantic understanding (via vector embeddings) with traditional keyword matching. It also has fuzzy search for typos, ranking based on relevance/recency, and can show you related snippets you might have forgotten about.

## Features

**Search & Discovery:**
- Natural language search - describe what you need, get what you meant
- Hybrid search combining semantic + keyword matching
- Automatic typo correction
- Related snippet suggestions
- Smart ranking that considers relevance, recency, and quality

**Managing Snippets:**
- Standard CRUD operations
- Interactive mode for multi-line code (opens your $EDITOR)
- Bulk indexing - point it at a directory and it'll extract functions/classes
- Auto-tagging based on code content
- Export/Import as JSON or Markdown
- Copy snippets directly to clipboard

**AI Providers:**
- Google Gemini (default) - text-embedding-004 + gemini-2.5-flash
- OpenAI - text-embedding-3-small/large + GPT-4o-mini
- Local models - 5 different sentence-transformers models, fully offline
- Automatic fallback from cloud to local
- Smart caching to save on API costs (reduces calls by 80%+)

**Other Stuff:**
- GitHub integration - import entire repos or individual gists
- Usage analytics and API cost tracking
- Backup/restore with vectors included
- Works with PostgreSQL or SQLite
- Connection pooling and caching for performance

## Installation

**From PyPI (easiest):**
```bash
pip install snipvault
snipvault init
```

**Docker:**
```bash
git clone https://github.com/yourusername/snipvault.git
cd snipvault
docker-compose up -d
docker exec -it snipvault-app snipvault init
```

**From source:**
```bash
git clone https://github.com/yourusername/snipvault.git
cd snipvault
pip install -r requirements.txt
python main.py init
```

## Configuration

You need to set up a few things before using it:

1. **Database** - Either PostgreSQL or SQLite

   For PostgreSQL:
   ```bash
   sudo apt-get install postgresql
   createdb snipvault
   ```

   For SQLite: nothing to do, it'll create the file automatically

2. **Environment variables** - Create a `.env` file:
   ```env
   # If using PostgreSQL
   POSTGRES_HOST=localhost
   POSTGRES_DB=snipvault
   POSTGRES_USER=your_user
   POSTGRES_PASSWORD=your_password

   # For vector search (optional, can use local embeddings)
   PINECONE_API_KEY=your_key
   PINECONE_ENVIRONMENT=us-east-1-aws

   # Pick one AI provider (or use local models)
   GEMINI_API_KEY=your_key     # Get from https://ai.google.dev/
   OPENAI_API_KEY=your_key     # Get from https://platform.openai.com/

   # For GitHub features (optional)
   GITHUB_TOKEN=your_token
   ```

3. **Config file** (optional) - Edit `~/.snipvault/config.yaml`:
   ```yaml
   embeddings:
     provider: gemini  # or openai, or local

   llm:
     provider: gemini

   cache:
     enabled: true
     ttl: 86400

   database:
     backend: postgresql  # or sqlite
   ```

**Running fully local:** Set `provider: local` in the config and don't worry about API keys. Models will download automatically (~100MB) on first use.

## Usage

**Add a snippet:**
```bash
# Interactive mode (opens your editor)
snipvault add --interactive

# Or inline
snipvault add \
  --title "FizzBuzz" \
  --code "for i in range(1,101): print('Fizz'*(i%3==0)+'Buzz'*(i%5==0) or i)" \
  --lang python \
  --tags algorithm,fizzbuzz
```

**Search:**
```bash
# Simple search
snipvault search "payment processing API"

# With filters
snipvault search "sorting algorithm" --lang python --tags algorithm

# Hybrid mode (semantic + exact keywords)
snipvault search "react hooks" --hybrid

# Pagination
snipvault search "database" --top 20 --page 2
```

**List everything:**
```bash
snipvault list
snipvault list --verbose  # shows full code
```

**View/edit/delete:**
```bash
snipvault show 5
snipvault show 5 --copy           # copy to clipboard
snipvault update 5 --edit         # edit in $EDITOR
snipvault update 5 --title "New"
snipvault delete 5
```

**Bulk operations:**
```bash
# Index an entire directory
snipvault index ~/projects/myapp

# With auto-tagging
snipvault index ~/code --auto-tag --exclude "node_modules,venv"

# Export/import
snipvault export snippets.json
snipvault export snippets.md --format markdown
snipvault import snippets.json
```

**GitHub integration:**
```bash
snipvault github-import user/repo
snipvault github-import user/repo --path src/utils

snipvault gist list
snipvault gist import gist_id
snipvault gist export 5 --public
```

**Stats and backup:**
```bash
snipvault stats
snipvault stats --days 30 --show-costs

snipvault backup create
snipvault backup create --include-vectors
snipvault backup restore backup-2025-11-09.tar.gz
```

## How it works

When you add a snippet:
1. Saves metadata (title, code, language, tags) to PostgreSQL/SQLite
2. Generates a 768-dimension vector embedding of the combined text
3. Stores the embedding in Pinecone with the snippet ID

When you search:
1. Your query gets enhanced by the LLM (adds synonyms, related terms)
2. Enhanced query converts to a 768-dim embedding
3. Pinecone finds the most similar vectors using cosine similarity
4. PostgreSQL fetches the full snippet details
5. Results get ranked and displayed with syntax highlighting

The cache layer sits in front of the embedding API, so repeated queries are basically free.

## Architecture

```
User Query
    ↓
Gemini LLM (enhance query)
    ↓
Gemini Embeddings (768 dims)
    ↓
Pinecone (vector similarity)
    ↓ (returns snippet IDs)
PostgreSQL (fetch metadata)
    ↓
Display with Rich
```

## Performance

- Add snippet: ~200ms (including embedding generation)
- Search (cached): ~50ms
- Search (API): ~500ms
- Index 100 files: ~30s

Cache hit rate is around 85% for common queries, which saves about 80% of API costs.

Supports 60+ languages including Python, JavaScript, TypeScript, Java, C++, C#, Go, Rust, Ruby, PHP, Swift, Kotlin, Scala, SQL, and more.