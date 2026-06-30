-- HNSW index for kb_chunks embeddings (run after sufficient data; safe to recreate)

DROP INDEX IF EXISTS public.idx_kb_chunks_embedding;

CREATE INDEX IF NOT EXISTS idx_kb_chunks_embedding_hnsw
    ON public.kb_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
