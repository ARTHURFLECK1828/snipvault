-- Migration: 001_advanced_search.sql
-- Purpose: Add full-text search capabilities and summary column
-- Date: 2025-11-09

-- Add full-text search vector column
-- Weight: A (highest) for title, B for code, C for tags
ALTER TABLE snippets
ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Create function to update search vector
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.code, '')), 'B') ||
        setweight(to_tsvector('english', array_to_string(NEW.tags, ' ')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update search vector
DROP TRIGGER IF EXISTS snippets_search_vector_update ON snippets;
CREATE TRIGGER snippets_search_vector_update
    BEFORE INSERT OR UPDATE ON snippets
    FOR EACH ROW
    EXECUTE FUNCTION update_search_vector();

-- Update existing rows with search vectors
UPDATE snippets SET search_vector =
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(code, '')), 'B') ||
    setweight(to_tsvector('english', array_to_string(tags, ' ')), 'C');

-- Create GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS snippets_fts_idx
ON snippets USING GIN(search_vector);

-- Add summary column for AI-generated summaries
ALTER TABLE snippets
ADD COLUMN IF NOT EXISTS summary TEXT;

-- Add usage tracking columns (for future ranking improvements)
ALTER TABLE snippets
ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0;

ALTER TABLE snippets
ADD COLUMN IF NOT EXISTS last_viewed TIMESTAMP;

-- Create view for search analytics
CREATE OR REPLACE VIEW search_quality AS
SELECT
    id,
    title,
    language,
    created_at,
    array_length(tags, 1) as tag_count,
    length(code) as code_length,
    summary IS NOT NULL as has_summary,
    view_count
FROM snippets;

-- Verify migration
DO $$
BEGIN
    RAISE NOTICE 'Migration 001_advanced_search completed successfully';
END $$;
