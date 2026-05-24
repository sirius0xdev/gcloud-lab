-- ============================================================
-- RAG Knowledge Base Schema for agent_memory database
-- Embedding dimensions: 768 (nomic-embed-text-v1.5)
-- ============================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table for RAG knowledge base
CREATE TABLE IF NOT EXISTS documents (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content       TEXT NOT NULL,
    metadata      JSONB DEFAULT '{}'::jsonb,
    embedding     vector(768),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index on content for full-text search
CREATE INDEX IF NOT EXISTS idx_documents_content ON documents USING gin (to_tsvector('english', content));

-- HNSW index for vector similarity search (cosine distance)
CREATE INDEX IF NOT EXISTS idx_documents_embedding_hnsw ON documents USING hnsw (embedding vector_cosine_ops);

-- Index on metadata for filtering
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING gin (metadata);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_documents_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_documents_updated_at();

-- Comments for documentation
COMMENT ON TABLE documents IS 'RAG knowledge base documents with vector embeddings';
COMMENT ON COLUMN documents.content IS 'Full text content of the document';
COMMENT ON COLUMN documents.metadata IS 'JSON metadata: source, chunk_id, title, tags, etc.';
COMMENT ON COLUMN documents.embedding IS '768-dim vector embedding (nomic-embed-text-v1.5)';

-- Example query for similarity search:
-- SELECT id, content, metadata, 1 - (embedding <=> 'your_embedding_here'::vector) AS similarity
-- FROM documents
-- ORDER BY embedding <=> 'your_embedding_here'::vector
-- LIMIT 5;
