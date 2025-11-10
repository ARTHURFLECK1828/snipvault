# SnipVault Quick Start Guide

Get up and running with SnipVault in 5 minutes!

## Prerequisites Checklist

- [ ] Python 3.8+ installed
- [ ] PostgreSQL 12+ installed and running
- [ ] Pinecone account ([sign up free](https://www.pinecone.io/))
- [ ] Google AI API key ([get it here](https://ai.google.dev/))

## Step-by-Step Setup

### 1. Run the Setup Script

```bash
./setup.sh
```

This will:
- Create a virtual environment
- Install all dependencies
- Create `.env` file from template

### 2. Configure API Keys

Edit `.env` file with your credentials:

```bash
nano .env  # or use your favorite editor
```

**Required settings:**

| Variable | Where to Get | Example |
|----------|--------------|---------|
| `DATABASE_URL` | Your PostgreSQL connection | `postgresql://user:pass@localhost:5432/snipvault` |
| `PINECONE_API_KEY` | [Pinecone Console](https://app.pinecone.io/) → API Keys | `12345678-abcd-...` |
| `PINECONE_ENVIRONMENT` | Pinecone Console → Index → Environment | `us-east-1-aws` |
| `GOOGLE_API_KEY` | [Google AI Studio](https://ai.google.dev/) → Get API Key | `AIzaSy...` |

### 3. Create PostgreSQL Database

```bash
# Option 1: Using createdb
createdb snipvault

# Option 2: Using psql
psql -U postgres -c "CREATE DATABASE snipvault;"
```

### 4. Initialize SnipVault

```bash
source venv/bin/activate
python main.py init
```

You should see:
```
✓ PostgreSQL database initialized successfully
✓ Created Pinecone index: snipvault
✓ All databases initialized successfully!
```

## Your First Snippet

### Add a Snippet

```bash
python main.py add "Python List Comprehension" \
  "squares = [x**2 for x in range(10)]" \
  --lang python \
  --tags python basics
```

### Search for It

```bash
python main.py search "square numbers in python"
```

Expected output:
```
→ Enhancing query with Gemini...
→ Generating query embedding...
→ Searching vector database...

Found 1 results:

[1] Python List Comprehension • (ID: 1) • python • similarity: 89%
┌─────────────────────────────────────────┐
│ squares = [x**2 for x in range(10)]    │
└─────────────────────────────────────────┘
```

### List All Snippets

```bash
python main.py list
```
### Add More Snippets

Try adding different types of code:

```bash
# JavaScript async function
python main.py add "Fetch API Example" \
  "async function fetchData(url) { const response = await fetch(url); return response.json(); }" \
  --lang javascript \
  --tags async api fetch

# SQL query
python main.py add "Count Users by Country" \
  "SELECT country, COUNT(*) as user_count FROM users GROUP BY country ORDER BY user_count DESC;" \
  --lang sql \
  --tags database aggregation

# Bash one-liner
python main.py add "Find Large Files" \
  "find . -type f -size +100M -exec ls -lh {} \;" \
  --lang bash \
  --tags filesystem utilities
```

### Try Natural Language Search

The power of SnipVault is semantic search:

```bash
# Instead of exact keywords, use natural language
python main.py search "how to make async API calls in JavaScript"
# → Finds the "Fetch API Example" snippet

python main.py search "find large files on disk"
# → Finds the bash snippet

python main.py search "count users by location"
# → Finds the SQL query
```

### Explore Options

```bash
# Get top 10 results
python main.py search "python" --top 10

# Disable query enhancement (faster, less accurate)
python main.py search "react hooks" --no-enhance

# List with full code
python main.py list --verbose

# Limit list results
python main.py list --limit 5
```

## Tips for Best Results

1. **Be descriptive in titles** - Helps with search accuracy
2. **Add relevant tags** - Tags are included in embeddings
3. **Use natural language for search** - "how to X" works better than keywords
4. **Experiment with query enhancement** - Try with/without `--no-enhance`

## Creating an Alias

For convenience, add to your `~/.bashrc` or `~/.zshrc`:

```bash
alias snipvault='cd /path/to/snipvault && source venv/bin/activate && python main.py'
```

Then you can just type:
```bash
snipvault search "API call"
snipvault add "My Snippet" "code here" --lang python
```