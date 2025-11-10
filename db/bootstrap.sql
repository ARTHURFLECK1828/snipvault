-- SnipVault Database Schema
-- This schema stores metadata for code snippets
-- Vector embeddings are stored in Pinecone

CREATE TABLE IF NOT EXISTS snippets (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    code TEXT NOT NULL,
    language TEXT DEFAULT 'plaintext',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster queries by language
CREATE INDEX IF NOT EXISTS idx_language ON snippets(language);

-- Index for faster queries by creation time
CREATE INDEX IF NOT EXISTS idx_created_at ON snippets(created_at DESC);

-- GIN index for array operations on tags
CREATE INDEX IF NOT EXISTS idx_tags ON snippets USING GIN(tags);
